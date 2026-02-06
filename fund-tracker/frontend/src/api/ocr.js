// OCR识别相关API
import request from './request.js'

export const ocrApi = {
  /**
   * 扫描图片识别基金
   * @param {string} imageBase64 - 图片的base64编码
   * @returns {Promise<Object>} 识别结果
   */
  scan(imageBase64) {
    return request({
      url: '/ocr/scan',
      method: 'POST',
      data: { image_base64: imageBase64 }
    })
  },

  /**
   * 识别并匹配基金（兼容旧接口）
   * @param {string} imageBase64 - 图片的base64编码
   * @returns {Promise<Object>} 匹配结果
   */
  extract(imageBase64) {
    return request({
      url: '/ocr/extract',
      method: 'POST',
      data: { image_base64: imageBase64 }
    })
  },

  /**
   * 识别持仓截图，提取完整持仓数据
   * @param {string} imageBase64 - 图片的base64编码
   * @returns {Promise<Object>} 持仓数据
   */
  extractPositions(imageBase64) {
    return request({
      url: '/ocr/extract-positions',
      method: 'POST',
      data: { image_base64: imageBase64 }
    })
  }
}

export default ocrApi
