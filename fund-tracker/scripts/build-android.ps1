# Build settings: only this process is configured; Conda base and global Java/SDK settings are untouched.
[CmdletBinding()]
param(
    [string]$SdkRoot = $(if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:USERPROFILE '.cache/fund-tracker/android-sdk' }),
    [string]$JdkRoot = $env:JAVA_HOME,
    [string]$PythonExecutable = $(Join-Path $env:USERPROFILE 'AppData/Local/miniforge3/envs/fund-tracker/python.exe'),
    [string]$NdkVersion = '28.2.13676358',
    [string]$ProxyUrl = $env:HTTPS_PROXY,
    [switch]$RebuildWheels
)

$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$frontend = Join-Path $project 'frontend'
$native = Join-Path $frontend 'src-tauri'
$wheels = Join-Path $native 'plugins/fund-backend/android/wheels'
$environmentNames = @('JAVA_HOME','ANDROID_HOME','NDK_HOME','FUND_TRACKER_BUILD_PYTHON','PATH','JAVA_TOOL_OPTIONS','CARGO_HTTP_PROXY','PYTHONUTF8','RUSTFLAGS','WRY_ANDROID_PACKAGE','TAURI_ANDROID_PACKAGE_UNESCAPED','WRY_ANDROID_LIBRARY','TAURI_ANDROID_PROJECT_PATH','WRY_ANDROID_KOTLIN_FILES_OUT_DIR','CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER','CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER','FUND_TRACKER_SIGNING_PASSWORD')
$oldEnvironment = @{}
foreach ($name in $environmentNames) { $oldEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

function Assert-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)" }
}

try {
    if (!(Test-Path -LiteralPath $PythonExecutable)) { throw 'Supply the named fund-tracker Python 3.11 interpreter with -PythonExecutable.' }
    & $PythonExecutable -c "import sys; assert sys.version_info[:2] == (3, 11), 'Python 3.11 is required'; assert 'envs' in sys.prefix and not sys.prefix.endswith('miniforge3'), 'Do not use Conda base'"
    Assert-Exit 'Python environment verification'
    if (!(Test-Path -LiteralPath (Join-Path $JdkRoot 'bin/java.exe'))) { throw 'Supply JDK 17 or newer with -JdkRoot; do not use the old global JAVA_HOME.' }
    $ndk = Join-Path $SdkRoot "ndk/$NdkVersion"
    if (!(Test-Path -LiteralPath (Join-Path $ndk 'source.properties'))) { throw "Install Android NDK $NdkVersion in $SdkRoot first." }
    $env:JAVA_HOME = $JdkRoot
    $env:ANDROID_HOME = $SdkRoot
    $env:NDK_HOME = $ndk
    $env:FUND_TRACKER_BUILD_PYTHON = $PythonExecutable
    $env:PYTHONUTF8 = '1'
    $env:PATH = "$JdkRoot/bin;$env:PATH"
    if ($ProxyUrl) {
        $proxy = [Uri]$ProxyUrl
        $env:JAVA_TOOL_OPTIONS = "$env:JAVA_TOOL_OPTIONS -Dhttp.proxyHost=$($proxy.Host) -Dhttp.proxyPort=$($proxy.Port) -Dhttps.proxyHost=$($proxy.Host) -Dhttps.proxyPort=$($proxy.Port)"
    }
    if ($RebuildWheels -or !(Test-Path (Join-Path $wheels 'pydantic_core-2.46.4-cp311-cp311-android_24_arm64_v8a.whl')) -or !(Test-Path (Join-Path $wheels 'pydantic_core-2.46.4-cp311-cp311-android_24_x86_64.whl'))) {
        & $PythonExecutable -u (Join-Path $PSScriptRoot 'build-android-wheels.py') --ndk $ndk
        Assert-Exit 'Android Python extension build'
    }
    if (!(Test-Path (Join-Path $native 'gen/android/gradlew.bat'))) {
        throw 'The Android project is missing. Restore the tracked gen/android project; do not regenerate over its native settings.'
    }
    Push-Location $frontend
    try {
        & npm.cmd run type-check
        Assert-Exit 'Frontend type check'
        & npm.cmd run tauri:build:web
        Assert-Exit 'Bundled frontend build'
        # Tauri's default CLI requires Windows symlink privileges. Compile the same real libraries,
        # then copy them instead; no developer mode, system privileges or remote backend is needed.
        $env:WRY_ANDROID_PACKAGE = 'com.fundtracker.app'
        $env:TAURI_ANDROID_PACKAGE_UNESCAPED = 'com.fundtracker.app'
        $env:WRY_ANDROID_LIBRARY = 'fund_tracker_lib'
        $env:TAURI_ANDROID_PROJECT_PATH = Join-Path $native 'gen/android'
        $env:WRY_ANDROID_KOTLIN_FILES_OUT_DIR = Join-Path $env:TAURI_ANDROID_PROJECT_PATH 'app/src/main/java/com/fundtracker/app/generated'
        $env:RUSTFLAGS = '-C link-arg=-Wl,-z,max-page-size=16384'
        $targets = @(@('aarch64-linux-android','arm64-v8a'), @('x86_64-linux-android','x86_64'))
        foreach ($target in $targets) {
            $linkerName = 'CARGO_TARGET_' + $target[0].ToUpper().Replace('-', '_') + '_LINKER'
            [Environment]::SetEnvironmentVariable($linkerName, (Join-Path $ndk "toolchains/llvm/prebuilt/windows-x86_64/bin/$($target[0])24-clang.cmd"), 'Process')
            & cargo.exe build --manifest-path (Join-Path $native 'Cargo.toml') --lib --release --target $target[0] --features tauri/custom-protocol --locked
            Assert-Exit "Android $($target[1]) native build"
            $dest = Join-Path $env:TAURI_ANDROID_PROJECT_PATH "app/src/main/jniLibs/$($target[1])"
            New-Item -ItemType Directory -Force $dest | Out-Null
            Copy-Item -LiteralPath (Join-Path $native "target/$($target[0])/release/libfund_tracker_lib.so") -Destination (Join-Path $dest 'libfund_tracker_lib.so') -Force
        }
        Push-Location $env:TAURI_ANDROID_PROJECT_PATH
        try {
            [IO.File]::WriteAllText((Join-Path $env:TAURI_ANDROID_PROJECT_PATH 'local.properties'), 'sdk.dir=' + $SdkRoot.Replace('\','/') + [Environment]::NewLine)
            [IO.File]::WriteAllText((Join-Path $env:TAURI_ANDROID_PROJECT_PATH 'app/tauri.properties'), "tauri.android.versionName=3.0.0`ntauri.android.versionCode=3000000`n")
            $pathHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($native))).Substring(0,12)
            $pythonBuild = Join-Path $env:USERPROFILE ".cache/fund-tracker/python-build/$pathHash"
            & ./gradlew.bat :app:assembleUniversalRelease '-PabiList=arm64-v8a,x86_64' '-ParchList=arm64,x86_64' '-PtargetList=aarch64,x86_64' "-PfundTrackerPythonBuildDir=$pythonBuild" -x :app:rustBuildArm64Release -x :app:rustBuildX86_64Release --no-configuration-cache --no-watch-fs --console=plain
            Assert-Exit 'Standalone APK assembly'
        } finally { Pop-Location }
    } finally { Pop-Location }

    # A stable private signing key allows subsequent versions to update without losing app data.
    $signing = Join-Path $native '.signing'
    New-Item -ItemType Directory -Force $signing | Out-Null
    $key = Join-Path $signing 'fund-tracker-release.p12'
    $secretFile = Join-Path $signing 'password.txt'
    if (!(Test-Path $key)) {
        if (Test-Path $secretFile) { throw 'Signing password exists but the key is missing. Restore the matching key before building an update.' }
        $bytes = New-Object byte[] 32
        [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
        $password = [Convert]::ToHexString($bytes)
        $env:FUND_TRACKER_SIGNING_PASSWORD = $password
        & (Join-Path $JdkRoot 'bin/keytool.exe') -genkeypair -keystore $key -storetype PKCS12 -alias fund-tracker -keyalg RSA -keysize 3072 -validity 10000 -dname 'CN=Fund Tracker' -storepass:env FUND_TRACKER_SIGNING_PASSWORD -keypass:env FUND_TRACKER_SIGNING_PASSWORD
        Assert-Exit 'Private release key generation'
        [IO.File]::WriteAllText($secretFile, $password)
    } else {
        if (!(Test-Path $secretFile)) { throw 'Restore .signing/password.txt matching the release key.' }
        $env:FUND_TRACKER_SIGNING_PASSWORD = [IO.File]::ReadAllText($secretFile).Trim()
    }
    $apks = @(Get-ChildItem (Join-Path $native 'gen/android/app/build/outputs/apk') -Recurse -Filter '*release-unsigned.apk')
    if ($apks.Count -ne 1) { throw "Expected one unsigned universal release APK, found $($apks.Count)." }
    $output = Join-Path $project 'dist/android'
    New-Item -ItemType Directory -Force $output | Out-Null
    $aligned = Join-Path $output 'fund-tracker-aligned.apk'
    $apk = Join-Path $output 'fund-tracker-3.0.0-universal.apk'
    $buildTools = Join-Path $SdkRoot 'build-tools/37.0.0'
    & (Join-Path $buildTools 'zipalign.exe') -f -P 16 4 $apks[0].FullName $aligned
    Assert-Exit '16 KB APK alignment'
    & (Join-Path $buildTools 'apksigner.bat') sign --v4-signing-enabled false --ks $key --ks-key-alias fund-tracker --ks-pass env:FUND_TRACKER_SIGNING_PASSWORD --key-pass env:FUND_TRACKER_SIGNING_PASSWORD --out $apk $aligned
    Assert-Exit 'APK signing'
    & (Join-Path $buildTools 'apksigner.bat') verify --verbose $apk
    Assert-Exit 'APK signature verification'
    Remove-Item -LiteralPath $aligned
    $hash = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLower()
    [IO.File]::WriteAllText((Join-Path $output 'SHA256SUMS.txt'), "$hash  $([IO.Path]::GetFileName($apk))" + [Environment]::NewLine)
    Write-Output "Signed standalone APK: $apk"
} finally {
    foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $oldEnvironment[$name], 'Process') }
}
