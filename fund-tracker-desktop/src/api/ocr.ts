import { request } from './request'

// OCR识别结果
export interface OcrScanResult {
  text: string
  confidence: number
}

// 提取的基金信息
export interface ExtractedFund {
  code: string
  name: string
  confidence: number
}

// OCR基金提取响应
export interface OcrFundExtractResponse {
  funds: ExtractedFund[]
  raw_text: string
  confidence: number
}

// OCR识别的持仓数据
export interface OcrPosition {
  fund_name: string
  fund_code?: string
  market_value?: number
  profit_amount?: number
  profit_rate?: number
  hold_shares?: number
  cost_nav?: number
  current_nav?: number
  cost_basis?: number
  confidence: number
}

// OCR持仓提取响应
export interface OcrPositionExtractResponse {
  positions: OcrPosition[]
  total_count: number
  matched_count: number
  raw_result?: {
    fund_codes: string[]
    fund_names: string[]
    raw_text: string
    confidence: number
  }
}

// API方法
export const ocrApi = {
  // OCR扫描图片识别文字
  scan(imageBase64: string): Promise<OcrScanResult> {
    return request.post('/ocr/scan', { image_base64: imageBase64 })
  },

  // OCR识别并提取基金信息（兼容旧接口）
  extractFunds(imageBase64: string): Promise<OcrFundExtractResponse> {
    return request.post('/ocr/extract', { image_base64: imageBase64 })
  },

  // OCR识别持仓截图，提取完整持仓数据
  extractPositions(imageBase64: string): Promise<OcrPositionExtractResponse> {
    return request.post('/ocr/extract-positions', { image_base64: imageBase64 })
  }
}

export default ocrApi
