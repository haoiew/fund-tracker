"""Build the pinned Pydantic extension for Android, never a host-platform substitute."""
import argparse
import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

# Build inputs: versions must match requirements-android.txt and the embedded Python minor version.
CORE_VERSION = "2.46.4"
CORE_SHA256 = "62f875393d7f270851f20523dd2e29f082bcc82292d66db2b64ea71f64b6e1c1"
PYTHON_TARGET = "3.11.17-0"
TARGETS = {
    "arm64-v8a": ("aarch64-linux-android", "399b58d04898f2c7d5f0044e141bdf3818552e538e5f36d06d7fe0bebc298582"),
    "x86_64": ("x86_64-linux-android", "a479a9c74ca9e900f30b6089ffd23a10d74fe7a9f427d967bceddf8f3fe206f1"),
}


def normalize_extension_name(wheel_path: Path) -> None:
    """Chaquopy 3.11 uses .cpython-311.so; the generic .so suffix is portable across both loaders."""
    with zipfile.ZipFile(wheel_path) as wheel:
        contents = {name: wheel.read(name) for name in wheel.namelist()}
    extension = next(name for name in contents if name.endswith('.so'))
    contents['pydantic_core/_pydantic_core.so'] = contents.pop(extension)
    record = next(name for name in contents if name.endswith('.dist-info/RECORD'))
    entries = []
    for name, data in contents.items():
        if name != record:
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            entries.append((name, 'sha256=' + digest, str(len(data))))
    entries.append((record, '', ''))
    output = io.StringIO(newline='')
    csv.writer(output).writerows(entries)
    contents[record] = output.getvalue().encode()
    with zipfile.ZipFile(wheel_path, 'w', compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, data in contents.items():
            wheel.writestr(name, data)


def download(url: str, path: Path, sha256: str) -> None:
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == sha256:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    except (OSError, urllib.error.URLError):
        if os.name != "nt":
            raise
        # Windows' system TLS stack is also a supported route for corporate/proxied networks.
        env = {**os.environ, "FUND_DOWNLOAD_URL": url, "FUND_DOWNLOAD_PATH": str(path)}
        subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command",
                        "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; "
                        "Invoke-WebRequest -Uri $env:FUND_DOWNLOAD_URL -OutFile $env:FUND_DOWNLOAD_PATH -TimeoutSec 120"],
                       env=env, check=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        raise RuntimeError(f"Checksum mismatch: {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/fund-tracker/pydantic-core")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] /
                        "frontend/src-tauri/plugins/fund-backend/android/wheels")
    parser.add_argument("--abi", choices=list(TARGETS), nargs="+", default=list(TARGETS))
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Use the project's named Python 3.11 environment, not Conda base")
    prebuilt = args.ndk / "toolchains/llvm/prebuilt" / ("windows-x86_64" if os.name == "nt" else "linux-x86_64")
    tools = prebuilt / "bin"
    if not (args.ndk / "source.properties").is_file() or not tools.is_dir():
        raise RuntimeError("Install the real Android NDK before building wheels")
    maturin = shutil.which("maturin") or str(Path(sys.executable).parent / "Scripts/maturin.exe")
    source = args.cache / f"pydantic_core-{CORE_VERSION}"
    archive = args.cache / f"pydantic_core-{CORE_VERSION}.tar.gz"
    download(f"https://files.pythonhosted.org/packages/source/p/pydantic-core/pydantic_core-{CORE_VERSION}.tar.gz",
             archive, CORE_SHA256)
    if not source.is_dir():
        with tarfile.open(archive) as package:
            package.extractall(args.cache, filter="data")
    args.output.mkdir(parents=True, exist_ok=True)
    for abi in args.abi:
        triple, target_digest = TARGETS[abi]
        target_archive = args.cache / f"target-{PYTHON_TARGET}-{abi}.zip"
        download(f"https://repo.maven.apache.org/maven2/com/chaquo/python/target/{PYTHON_TARGET}/{target_archive.name}",
                 target_archive, target_digest)
        library_dir = args.cache / "python-libs" / abi
        library_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target_archive) as package:
            library = next(name for name in package.namelist() if name.endswith("/libpython3.11.so"))
            (library_dir / "libpython3.11.so").write_bytes(package.read(library))
        config = args.cache / f"pyo3-{abi}.txt"
        config.write_text("implementation=CPython\nversion=3.11\nshared=true\nabi3=false\n"
                          f"lib_name=python3.11\nlib_dir={library_dir.resolve().as_posix()}\n"
                          "pointer_width=64\nbuild_flags=\n", encoding="utf-8")
        linker = tools / (triple + "24-clang" + (".cmd" if os.name == "nt" else ""))
        env = {**os.environ, "PYO3_CONFIG_FILE": str(config.resolve()),
               "PYO3_CROSS": "1", "ANDROID_API_LEVEL": "24",
               "CARGO_TARGET_" + triple.upper().replace("-", "_") + "_LINKER": str(linker),
               "CC_" + triple.replace("-", "_"): str(linker),
               "AR_" + triple.replace("-", "_"): str(tools / ("llvm-ar.exe" if os.name == "nt" else "llvm-ar")),
               "PATH": str(tools) + os.pathsep + os.environ.get("PATH", ""),
               "RUSTFLAGS": "-C link-arg=-Wl,-z,max-page-size=16384"}
        print(f"Building actual Android {abi} Python 3.11 extension...", flush=True)
        subprocess.run([maturin, "build", "--locked", "--release", "--target", triple,
                        "--features", "pyo3/extension-module", "--auditwheel", "skip",
                        "--out", str(args.output.resolve())], cwd=source, env=env, check=True)
        wheels = list(args.output.glob(f"pydantic_core-{CORE_VERSION}-cp311-cp311-android_24_{abi.replace('-', '_')}.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected exactly one Android {abi} wheel, got {wheels}")
        with zipfile.ZipFile(wheels[0]) as wheel:
            binaries = [name for name in wheel.namelist() if name.endswith(".so")]
            if not binaries:
                raise RuntimeError("The wheel has no native extension")
            binary = wheel.read(binaries[0])
            # ELF e_machine: Android ARM64=183, x86-64=62; PE/host binaries cannot pass.
            if binary[:4] != b"\x7fELF" or int.from_bytes(binary[18:20], "little") != (183 if abi == "arm64-v8a" else 62):
                raise RuntimeError("Wrong-platform native extension")
        print(f"Verified Android ELF in {wheels[0].name}", flush=True)
        normalize_extension_name(wheels[0])


if __name__ == "__main__":
    main()
