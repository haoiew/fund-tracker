## 问题分析

### 问题1：QDII基金显示"获取中"
从截图看，007722等基金显示"获取中"，数据源显示为"tiantian"。这是因为：
- 前端有缓存，存储了旧的数据
- 需要清除浏览器缓存或添加缓存过期机制

### 问题2：OCR导入功能报错
错误：`ocrApi.recognize is not a function`

原因：
1. 前端缺少 `ocr.js` API 文件
2. `portfolio.vue` 中没有图片上传和 OCR 调用功能

## 修复方案

### 1. 创建 OCR API 文件
创建 `frontend/src/api/ocr.js`：
```javascript
import request from './request.js'

export const ocrApi = {
  // 识别图片中的基金
  recognize(imageBase64) {
    return request({
      url: '/ocr/extract-positions',
      method: 'POST',
      data: { image_base64: imageBase64 }
    })
  }
}
```

### 2. 修改 portfolio.vue
添加：
- 图片选择功能
- OCR 识别调用
- 识别结果自动填充表单

### 3. 添加缓存清除机制
在获取数据时，如果数据状态为"获取中"超过一定时间，强制刷新

## 文件修改清单

1. `frontend/src/api/ocr.js` - 新建 OCR API 文件
2. `frontend/src/pages/portfolio/portfolio.vue` - 添加图片上传和 OCR 功能
3. `frontend/src/pages/index/index.vue` - 添加强制刷新机制

请确认后我将实施修复。