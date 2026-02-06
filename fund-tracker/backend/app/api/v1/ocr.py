# -*- coding: utf-8 -*-
"""
OCR识别相关API接口
"""
from fastapi import APIRouter, HTTPException

from app.schemas.common import (
    ResponseModel, 
    OcrScanRequest, 
    OcrScanResponse, 
    OcrFundExtractResponse,
    OcrPositionExtractResponse
)
from app.services.ocr_service import ocr_service

router = APIRouter()


@router.post("/scan", response_model=ResponseModel[OcrScanResponse])
async def scan_image(request: OcrScanRequest):
    """OCR扫描图片识别基金"""
    try:
        result = ocr_service.scan_image(request.image_base64)
        response = OcrScanResponse(**result)
        return ResponseModel(data=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")


@router.post("/extract", response_model=ResponseModel[OcrFundExtractResponse])
async def extract_funds(request: OcrScanRequest):
    """OCR识别并匹配基金（兼容旧接口）"""
    try:
        result = ocr_service.process_screenshot(request.image_base64)
        # 转换为旧格式
        from app.schemas.common import OcrFundMatch
        matches = []
        for pos in result.get("positions", []):
            matches.append(OcrFundMatch(
                extracted_text=pos["fund_name"],
                matched_fund={"code": pos["fund_code"], "name": pos["fund_name"]} if pos["fund_code"] else None,
                confidence=pos["confidence"]
            ))
        
        return ResponseModel(data={
            "matches": matches,
            "total_found": result.get("matched_count", 0)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"基金提取失败: {str(e)}")


@router.post("/extract-positions", response_model=ResponseModel[OcrPositionExtractResponse])
async def extract_positions(request: OcrScanRequest):
    """
    OCR识别持仓截图，提取完整持仓数据
    
    识别字段：
    - 基金名称
    - 当前市值
    - 持有收益金额
    - 持有收益率
    - 基金代码（通过名称匹配）
    """
    try:
        result = ocr_service.process_screenshot(request.image_base64)
        return ResponseModel(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"持仓提取失败: {str(e)}")
