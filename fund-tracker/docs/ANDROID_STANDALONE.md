# 独立安卓安装包

## 安装与运行

发布文件位于 `fund-tracker/dist/android/fund-tracker-3.0.0-universal.apk`，同时提供 `SHA256SUMS.txt` 校验值。它包含 Vue 界面、Python 3.11、FastAPI 本地服务、SQLite 和实际使用的数据处理依赖，不是指向电脑服务的网页外壳。

- 安装后直接打开，无需电脑后端、Termux、Python、Node.js 或 Android Studio。
- 支持 ARM64 和 x86_64，最低 Android 7.0；系统 WebView 应保持更新。32 位设备不在本次包的范围内。
- 实时行情和 AI 识别仍需要网络。AI 配置由用户在应用内填写，不会打入开发电脑上的密钥。
- 首页、筛选、比较、持仓、设置、关于沿用 Web 版模块；竖屏切换按钮仍在底栏。
- 第一次打开需要解压内置 Python 组件。再次启动复用应用私有存储中的数据库和关注列表。

## 数据与安全边界

应用启动时通过 Tauri 原生插件启动真实 FastAPI 服务，只绑定 `127.0.0.1` 的随机端口。前端自动接入，不需要配置服务器。每个进程生成临时访问令牌，其他应用不能直接访问持仓 API。

SQLite 和 `funds.txt` 写入 Android 应用私有 `files` 目录，不写入打包源代码目录。构建只复制 `backend/app`，不包含桌面 `.env`、数据库、关注列表、测试数据或密钥。Android 自动云备份已关闭；卸载或清除应用数据会删除本机记录。

CSV/JSON 导出使用 Android 系统文件保存对话框，无需申请整个存储空间的访问权限。用户取消保存时不显示导出成功。

后台刷新只在应用进程存活时运行；本包不承诺在被系统杀死后仍持续采集，也没有新增常驻通知服务。市场日期与日净值更新调度使用上海时区。

## 构建

构建工具只用于开发电脑，不是手机端的安装依赖。

需要 Node.js、Rust 的 `aarch64-linux-android` / `x86_64-linux-android` 目标、JDK 17、Android SDK 36 与 37.0、Build-Tools 36 / 37.0.0、NDK 28.2.13676358，以及项目的具名 Python 3.11 环境。首次构建还需安装 Maturin，优先在该环境使用 `mamba install -c conda-forge maturin`。不得使用 Conda base。

在项目根目录执行：

```powershell
.\fund-tracker\scripts\build-android.ps1 `
  -SdkRoot "$env:USERPROFILE/.cache/fund-tracker/android-sdk" `
  -JdkRoot 'C:/Program Files/Eclipse Adoptium/jdk-17.0.16.8-hotspot' `
  -PythonExecutable "$env:USERPROFILE/AppData/Local/miniforge3/envs/fund-tracker/python.exe"
```

按本机安装位置调整参数。有代理时可传 `-ProxyUrl`；仅影响构建进程，不修改全局 Java、SDK 或 Conda 设置。

构建脚本完成：

1. 编译并校验真正的 Android Pydantic Core，绝不替换成 Windows/Linux 桌面二进制。
2. 类型检查与 Vite 资源打包。
3. 编译两个架构的 Tauri 原生库，复制产物后由 Gradle 组装；不需要开启 Windows 开发者模式或取得符号链接权限。
4. 将 Python 构建中间文件放入独立用户缓存，避免 Windows 工程索引器占用移动中的目录。
5. 检查发布包、执行 16 KB ZIP 对齐、使用稳定的本地私钥签名、验证签名并输出 SHA-256。

签名私钥和密码位于被 Git 忽略的 `frontend/src-tauri/.signing`。请安全备份整个目录；发布更新必须使用相同的密钥，否则无法直接覆盖安装并保留数据。不要提交或公开该目录。

`src-tauri/gen/android` 中的原生配置已纳入工程；不要重新运行初始化命令覆盖安全区、网络策略和构建配置。生成的 Kotlin 桥接文件、JNI 库、Gradle 缓存和本机路径不纳入 Git。

## 依赖适配

NumPy / Pandas / Greenlet 使用可用的 Android 版本，其他 Python 依赖锁定到验证过的版本。Pydantic Core 由 `build-android-wheels.py` 使用真实 NDK 与 Chaquopy Python 库交叉编译，检查 ELF 架构，并使用兼容 Chaquopy 导入器的扩展文件名。

基金比较的指数日线和全市场排行直接读取实际公开数据接口，避免在 APK 中引入 AKShare 的非安卓依赖。单位净值、累计净值和估算口径仍由共享后端统一处理，不添加模拟行情。

## 验证边界

已完成完整构建脚本重跑、发布包签名验证、私密文件排除检查及 Android 15 / x86_64 模拟器冷启动。界面能切换到筛选页，底栏与系统状态栏/导航栏不再重叠；内置 Python 创建了应用私有数据库，调度器正常启动，冷启动不再触发时区探测子进程的信号重置告警。前端 25 项测试和后端 139 项非联网/非慢速测试通过。

当前模拟器的外部网络连接受限，真实行情、搜索结果、持仓完整操作和系统文件保存的端到端链路尚未完成联网实测；不将空结果或截图当作行情可用证据。ARM64 已完成真实交叉编译，但没有连接实体手机；特殊厂商系统、旧 WebView 和 16 KB 内存页设备仍需实体设备验证。

原生集成依据 [Tauri 移动插件接口](https://v2.tauri.app/develop/plugins/develop-mobile/) 和 [Chaquopy Android 集成说明](https://chaquo.com/chaquopy/doc/current/android.html)。
