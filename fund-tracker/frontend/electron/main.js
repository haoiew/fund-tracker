const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')

if (process.env.VITE_DEV_SERVER_URL) {
  const userDataDir = path.join(__dirname, '..', '.electron-user-data')
  app.commandLine.appendSwitch('user-data-dir', userDataDir)
  app.setPath('userData', userDataDir)
}

// 保持窗口对象的全局引用，防止被垃圾回收
let mainWindow

function createWindow() {
  // 创建浏览器窗口
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1280,
    minHeight: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset', // macOS 风格标题栏
    show: false, // 先不显示，等加载完成后再显示
    backgroundColor: '#1a1a2e' // 深色背景，减少白屏闪烁
  })

  // 加载应用
  if (process.env.VITE_DEV_SERVER_URL) {
    // 开发环境
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    // 生产环境
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 窗口加载完成后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    
    // 如果是2K屏幕，自动调整窗口大小
    const { screen } = require('electron')
    const primaryDisplay = screen.getPrimaryDisplay()
    const { width, height } = primaryDisplay.workAreaSize
    
    if (width >= 2560 && height >= 1440) {
      mainWindow.setSize(1800, 1100)
      mainWindow.center()
    }
  })

  // 窗口关闭时
  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Electron 初始化完成
app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    // macOS: 点击 dock 图标时重新创建窗口
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 所有窗口关闭时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC 通信处理
ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

ipcMain.handle('get-platform', () => {
  return process.platform
})
