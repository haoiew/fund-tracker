# 基金跟踪器安卓部署指南

## 📋 部署前准备

### 1. 环境要求

- **HBuilderX** (最新版): https://www.dcloud.io/hbuilderx.html
- **Node.js** 18+
- **后端服务**: 已部署并可公网访问
- **安卓证书**: 正式发布需要，测试可使用公共证书

### 2. 配置后端服务地址

编辑 `frontend/.env.production` 文件：

```env
# 修改为实际的后端服务器地址
VITE_API_BASE_URL=http://your-server-ip:8001/api/v1
```

**注意**: 安卓真机无法访问 `localhost`，必须使用公网IP或域名。

---

## 🚀 部署步骤

### 方式一：HBuilderX 云打包（推荐）

#### 步骤 1: 导入项目

1. 打开 HBuilderX
2. 文件 → 导入 → 从本地目录导入
3. 选择 `fund-tracker/frontend` 目录

#### 步骤 2: 配置应用信息

1. 打开 `manifest.json`
2. 配置以下信息：
   - **应用名称**: 基金跟踪器
   - **版本号**: 2.0.0
   - **AppID**: 登录 DCloud 账号后获取

#### 步骤 3: 发行打包

1. 点击菜单栏 `发行` → `原生App-云打包`
2. 选择 `Android (apk)`
3. 证书选择：
   - **测试**: 使用公共测试证书
   - **正式**: 使用自有证书（.keystore 文件）
4. 点击 `打包`
5. 等待打包完成，下载 APK 文件

#### 步骤 4: 安装测试

1. 将 APK 文件传输到安卓手机
2. 允许安装未知来源应用
3. 安装并测试

---

### 方式二：CLI 命令行打包

```bash
# 进入前端目录
cd fund-tracker/frontend

# 安装依赖
npm install

# 构建安卓应用
npm run build:app
```

构建完成后，使用 Android Studio 打开 `dist/build/app` 目录进行打包。

---

## 🔧 安卓权限说明

`manifest.json` 中已配置的权限：

| 权限 | 用途 |
|------|------|
| `INTERNET` | 网络访问，获取基金数据 |
| `CAMERA` | OCR截图识别功能 |
| `ACCESS_NETWORK_STATE` | 检测网络状态 |
| `WRITE_EXTERNAL_STORAGE` | 保存图片/数据 |

---

## ☁️ 免费云服务器推荐

### 1. 阿里云 - 学生/新用户免费套餐

- **免费额度**: 1核2G 云服务器，1个月免费
- **申请条件**: 学生认证或新用户
- **网址**: https://www.aliyun.com/

### 2. 腾讯云 - 轻量应用服务器

- **免费额度**: 新用户可领取免费试用
- **配置**: 2核2G 轻量服务器
- **网址**: https://cloud.tencent.com/

### 3. 华为云 - 免费试用

- **免费额度**: 1个月免费云服务器
- **申请条件**: 新用户注册
- **网址**: https://www.huaweicloud.com/

### 4. Oracle Cloud - 永久免费套餐

- **免费额度**: 2台 AMD 虚拟机（1核1G）永久免费
- **优点**: 无需信用卡，永久免费
- **网址**: https://www.oracle.com/cloud/free/

### 5. Vercel / Railway - 免费部署后端

- **适用**: 部署 FastAPI 后端
- **优点**: 无需管理服务器，自动部署
- **限制**: 有请求次数限制

---

## 📱 测试检查清单

部署完成后，请检查以下功能：

- [ ] 应用正常启动
- [ ] 基金列表能正常加载
- [ ] 实时估值数据显示正确
- [ ] 持仓管理功能正常
- [ ] OCR识别功能可用
- [ ] 图表正常显示

---

## ❓ 常见问题

### Q1: 应用无法连接后端服务？

**A**: 检查 `.env.production` 中的 `VITE_API_BASE_URL` 是否为公网可访问地址。

### Q2: 打包失败？

**A**: 
1. 确保已登录 DCloud 账号
2. 检查 `manifest.json` 配置是否正确
3. 查看 HBuilderX 控制台错误日志

### Q3: 安装后闪退？

**A**:
1. 检查安卓版本兼容性（最低 Android 5.0）
2. 检查是否授予必要权限
3. 查看安卓日志排查问题

### Q4: 如何更新应用？

**A**: 
1. 修改版本号（`manifest.json` 中的 `versionCode` 和 `versionName`）
2. 重新打包
3. 安装新版 APK（会自动覆盖旧版）

---

## 📞 技术支持

如有问题，请查看：
- UniApp 官方文档: https://uniapp.dcloud.net.cn/
- HBuilderX 文档: https://www.dcloud.io/hbuilderx.html
