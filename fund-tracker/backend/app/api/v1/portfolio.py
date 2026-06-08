# -*- coding: utf-8 -*-
"""
持仓API - 单用户本地工具
"""
import asyncio
import json
import re
import time
from difflib import SequenceMatcher
from typing import List
from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse, PortfolioProfitResponse,
    AiRecognizeRequest, AiRecognizeResponse, AiRecognizeHolding,
    AiConnectionTestRequest, AiConnectionTestResponse,
    PortfolioTransactionCreate, PortfolioTransactionResponse,
    PortfolioImportConfirmRequest, PortfolioImportConfirmResponse,
    PortfolioImportPreviewRequest, PortfolioImportPreviewResponse
)
from app.schemas.common import ResponseModel
from app.services.portfolio_service import PortfolioServiceError, portfolio_service
from app.logger import get_logger

router = APIRouter()
logger = get_logger("api.portfolio")

_NOISE_WORDS = (
    "证券投资基金", "开放式", "联接", "基金", "混合型", "股票型", "债券型", "指数型",
    "发起式", "增强", "lof", "etf", "qdii", "fof", "人民币"
)

_FUND_STYLE_WORDS = (
    "混合型", "混合", "股票型", "股票", "债券型", "债券", "指数型", "指数",
    "发起式", "发起", "联接", "基金", "lof", "etf", "qdii", "fof", "人民币"
)

_AI_REQUEST_TIMEOUT = httpx.Timeout(connect=15, read=180, write=60, pool=10)
_AI_TEST_TIMEOUT = httpx.Timeout(connect=5, read=15, write=10, pool=5)
_AI_VISION_TEST_TIMEOUT = httpx.Timeout(connect=10, read=60, write=20, pool=5)

DEFAULT_AI_RECOGNIZE_PROMPT = (
    '你是基金持仓截图识别器。请从这张基金持仓截图中提取“我的持有”列表里的每一只基金，返回严格JSON，不要包含解释、Markdown或代码块。'
    '只读取列表行，不要把顶部“总金额、昨日收益、持有收益、累计收益”当成基金。'
    '先读取“全部(n)”中的n作为expected_count；如果截图显示全部(18)，holdings必须返回18条，除非某行完全不可见。'
    '每条记录必须带row_index，从列表第一只基金开始按从上到下编号；不要合并名称相似或重复出现的基金。'
    '截图列表通常有三列：左列是基金名称；中列是“金额/昨日收益”，第一行是当前金额market_value，第二行是昨日收益daily_return；'
    '右列是“持仓收益/率”，第一行是持有收益holding_return，第二行是持有收益率holding_return_rate。'
    '红色加号为正数，绿色减号为负数，必须保留正负号；数字中的逗号去掉。'
    '名称可能换行，例如“南方香港优选股票(QDII-LOF)”必须合并成一个名称。'
    'A类、C类、QDII、LOF、ETF、FOF、人民币这些后缀会影响基金代码，能看到时必须保留。'
    '如果基金名称被省略号、括号截断或看不完整，不要猜全名或A/C类别，原样填写raw_fund_name和fund_name。'
    'JSON结构：{"expected_count":18,"holdings":[{"row_index":1,"fund_name":"基金名称","raw_fund_name":"截图原始名称","market_value":金额数字,'
    '"daily_return":昨日收益数字,"holding_return":持有收益数字,"holding_return_rate":收益率数字或null}]}。'
    '无法识别的数字填0，无法识别的收益率填null。'
)

_VISION_TEST_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAUElEQVR4nGMQIREwQKivRACEBgiHoGoIyQBXikcPshoGZHVY9aApYEBTRJCLrgHNAZhSWDR8hQUIVnFqaCDNSaR5mrRgJS3iSEsaJCc+kgAAW+73CGUip7AAAAAASUVORK5CYII="
)


def _normalize_ai_model_id(model: str) -> str:
    stripped = (model or "").strip()
    if re.match(r"^gpt-", stripped, flags=re.IGNORECASE):
        return stripped.lower()
    return stripped


def _join_ai_url(base_url: str, path: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    normalized_path = path.strip("/")
    if cleaned.endswith(normalized_path):
        return cleaned
    return f"{cleaned}/{normalized_path}"


def _extract_ai_error_message(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except ValueError:
        text = resp.text.strip()
        return text[:300] if text else f"HTTP {resp.status_code}"

    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("code") or str(error)
    elif isinstance(error, str):
        message = error
    elif isinstance(data, dict):
        message = data.get("message") or data.get("detail") or str(data)
    else:
        message = str(data)
    return str(message)[:300]


async def _call_ai_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: httpx.Timeout,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[dict, int, int]:
    normalized_model = _normalize_ai_model_id(model)
    payload = {
        "model": normalized_model,
        "messages": messages,
        **({"temperature": temperature} if temperature is not None else {}),
        **({"max_completion_tokens": max_tokens} if max_tokens is not None else {})
    }
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            _join_ai_url(base_url, "/chat/completions"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code >= 400:
        message = _extract_ai_error_message(resp)
        if resp.status_code == 503:
            message = (
                f"{message}。上游返回 503，通常表示 Base URL 当前没有把模型 {normalized_model} "
                "路由到可用服务，或模型临时不可用；请先在该服务商后台确认模型列表/额度/线路。"
            )
        raise HTTPException(
            status_code=502,
            detail=f"AI API调用失败: HTTP {resp.status_code} - {message}"
        )
    try:
        return resp.json(), latency_ms, resp.status_code
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"AI API返回不是有效JSON: {str(e)}")


def _normalize_fund_name(name: str) -> str:
    normalized = re.sub(r"[\s（）()【】\[\]·,，.。_-]+", "", (name or "").lower())
    for word in _NOISE_WORDS:
        normalized = normalized.replace(word, "")
    normalized = normalized.replace("a类", "a").replace("c类", "c")
    normalized = re.sub(r"(东方红中证)东方红", r"\1", normalized)
    normalized = normalized.replace("东方红红利", "东方红中证红利")
    return normalized


def _extract_share_class(name: str) -> str:
    text = re.sub(r"[\s（）()【】\[\]·,，.。_-]+", "", (name or "").lower())
    match = re.search(r"(a|c)类?$", text)
    return match.group(1).upper() if match else ""


def _build_fund_search_keyword(name: str) -> str:
    keyword = (name or "").strip()
    for marker in ("…", "..."):
        if marker in keyword:
            keyword = keyword.split(marker, 1)[0]
            break
    keyword = re.sub(r"[（(]\s*$", "", keyword).strip()
    return keyword or (name or "").strip()


def _build_fund_search_keywords(name: str) -> list[str]:
    primary = _build_fund_search_keyword(name)
    compact = re.sub(r"[\s（）()【】\[\]·,，.。_-]+", "", primary).strip()
    without_style = compact
    for word in _FUND_STYLE_WORDS:
        without_style = re.sub(re.escape(word), "", without_style, flags=re.IGNORECASE)

    share_class = _extract_share_class(primary)
    stem_without_class = re.sub(r"(A|C|a|c)类?$", "", without_style)
    candidates = [
        primary,
        re.sub(r"[（(].*?[）)]", "", primary).strip(),
        compact,
        without_style,
        stem_without_class,
    ]
    if share_class and len(stem_without_class) >= 4:
        candidates.append(f"{stem_without_class}{share_class}")
    if len(primary) > 8:
        candidates.append(primary[:12])
        candidates.append(primary[:8])
    if len(stem_without_class) >= 4:
        candidates.append(stem_without_class[:6])
        candidates.append(stem_without_class[:4])

    seen: set[str] = set()
    keywords: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            keywords.append(candidate)
    return keywords


def _is_ordered_subsequence(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    position = 0
    for char in haystack:
        if position < len(needle) and needle[position] == char:
            position += 1
    return position == len(needle)


def _score_fund_match(query_name: str, candidate_name: str) -> tuple[int, str]:
    query = _normalize_fund_name(query_name)
    candidate = _normalize_fund_name(candidate_name)
    if not query or not candidate:
        return 0, "empty"
    query_class = _extract_share_class(query_name)
    candidate_class = _extract_share_class(candidate_name)
    if query == candidate:
        score = 100
        reason = "normalized_exact"
    elif len(query) >= 6 and len(candidate) >= 6 and (query in candidate or candidate in query):
        score = 92
        reason = "strong_contains"
    elif len(query) >= 4 and _is_ordered_subsequence(query, candidate):
        score = 88
        reason = "ordered_subsequence"
    else:
        ratio = SequenceMatcher(None, query, candidate).ratio()
        score = int(ratio * 100)
        reason = "similarity"

    if query_class and candidate_class:
        if query_class != candidate_class:
            return min(score, 82), f"{reason}:share_class_mismatch"
        return min(100, score + 5), f"{reason}:share_class_match"
    if query_class and not candidate_class:
        return min(score, 90), f"{reason}:candidate_missing_share_class"
    if not query_class and candidate_class:
        return min(score, 94), f"{reason}:query_missing_share_class"
    return score, reason


def _match_fund_candidate(fund_name: str, search_results: list[dict]) -> tuple[str, str, str, int, list[dict]]:
    candidates = []
    for result in search_results[:12]:
        name = result.get("name", "")
        code = result.get("code", "")
        score, reason = _score_fund_match(fund_name, name)
        candidates.append({"code": code, "name": name, "score": score, "reason": reason})

    candidates.sort(key=lambda item: item["score"], reverse=True)
    if not candidates:
        return "", fund_name, "not_found", 0, []

    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0
    is_confident = top["score"] >= 92 and (top["score"] - second_score >= 8 or top["score"] == 100)
    if is_confident:
        return top["code"], top["name"], "matched", top["score"], candidates
    return "", fund_name, "ambiguous", top["score"], candidates


def _search_fund_candidates(fund_service, fund_name: str, limit: int = 12) -> tuple[str, list[dict]]:
    merged: list[dict] = []
    seen_codes: set[str] = set()
    used_keyword = ""
    for keyword in _build_fund_search_keywords(fund_name):
        results = fund_service.search_funds(keyword, limit=limit)
        if results and not used_keyword:
            used_keyword = keyword
        for result in results:
            code = str(result.get("code", ""))
            if code and code not in seen_codes:
                seen_codes.add(code)
                merged.append(result)
        if len(merged) >= limit:
            break
    return used_keyword or _build_fund_search_keyword(fund_name), merged[:limit]


def _to_float(value, default: float = 0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = (
        text.replace(",", "")
        .replace("，", "")
        .replace("￥", "")
        .replace("¥", "")
        .replace("%", "")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("﹣", "-")
        .replace("元", "")
        .replace(" ", "")
    )
    try:
        return float(text)
    except ValueError:
        return default


async def _build_portfolio_summary(db: Session) -> dict:
    """Shared helper for summary and refresh endpoints."""
    from app.services.fund_service import get_fund_service
    portfolios = portfolio_service.get_all_portfolios(db)

    # Fetch realtime data once for all funds
    codes = [p.fund_code for p in portfolios]
    rt_list = await get_fund_service().get_realtime_batch(codes)
    rt_map = {code: rt for code, rt in zip(codes, rt_list)}

    items = await asyncio.gather(*[portfolio_service.to_response(p, rt_map.get(p.fund_code)) for p in portfolios])
    profit_data = await portfolio_service.calculate_portfolio_profit(db, rt_map)
    stats = {
        "total_cost": float(profit_data.summary.total_cost),
        "total_value": float(profit_data.summary.total_value),
        "total_profit_loss": float(profit_data.summary.total_profit),
        "total_profit_loss_pct": float(profit_data.summary.total_profit_rate),
        "item_count": profit_data.summary.fund_count
    }
    return {"items": items, "stats": stats}


@router.post("", response_model=ResponseModel[PortfolioResponse])
async def create_portfolio(portfolio: PortfolioCreate, db: Session = Depends(get_db)):
    try:
        db_portfolio = portfolio_service.create_portfolio(db, portfolio)
    except PortfolioServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ResponseModel(data=await portfolio_service.to_response(db_portfolio))


@router.get("", response_model=ResponseModel[List[PortfolioResponse]])
async def get_portfolios(db: Session = Depends(get_db)):
    portfolios = portfolio_service.get_all_portfolios(db)
    items = await asyncio.gather(*[portfolio_service.to_response(p) for p in portfolios])
    return ResponseModel(data=list(items))


@router.get("/profit", response_model=ResponseModel[PortfolioProfitResponse])
async def get_portfolio_profit(db: Session = Depends(get_db)):
    return ResponseModel(data=await portfolio_service.calculate_portfolio_profit(db))


@router.get("/summary", response_model=ResponseModel[dict])
async def get_portfolio_summary(db: Session = Depends(get_db)):
    return ResponseModel(data=await _build_portfolio_summary(db))


@router.post("/transactions", response_model=ResponseModel[PortfolioTransactionResponse])
async def create_portfolio_transaction(transaction: PortfolioTransactionCreate, db: Session = Depends(get_db)):
    try:
        db_transaction = portfolio_service.create_transaction(db, transaction)
    except PortfolioServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ResponseModel(data=portfolio_service.to_transaction_response(db_transaction))


@router.post("/import/preview", response_model=ResponseModel[PortfolioImportPreviewResponse])
async def preview_portfolio_import(request: PortfolioImportPreviewRequest, db: Session = Depends(get_db)):
    return ResponseModel(data=await portfolio_service.preview_import(db, request))


@router.post("/import/confirm", response_model=ResponseModel[PortfolioImportConfirmResponse])
async def confirm_portfolio_import(request: PortfolioImportConfirmRequest, db: Session = Depends(get_db)):
    try:
        return ResponseModel(data=await portfolio_service.confirm_import(db, request))
    except PortfolioServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{portfolio_id}/transactions", response_model=ResponseModel[List[PortfolioTransactionResponse]])
async def get_portfolio_transactions(portfolio_id: int, db: Session = Depends(get_db)):
    if not portfolio_service.get_portfolio(db, portfolio_id):
        raise HTTPException(status_code=404, detail="持仓不存在")
    transactions = portfolio_service.get_transactions(db, portfolio_id)
    return ResponseModel(data=[portfolio_service.to_transaction_response(t) for t in transactions])


@router.get("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = portfolio_service.get_portfolio(db, portfolio_id)
    if not p:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(data=await portfolio_service.to_response(p))


@router.put("/{portfolio_id}", response_model=ResponseModel[PortfolioResponse])
async def update_portfolio(portfolio_id: int, portfolio_update: PortfolioUpdate, db: Session = Depends(get_db)):
    try:
        updated = portfolio_service.update_portfolio(db, portfolio_id, portfolio_update)
    except PortfolioServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(data=await portfolio_service.to_response(updated))


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    if not portfolio_service.delete_portfolio(db, portfolio_id):
        raise HTTPException(status_code=404, detail="持仓不存在")
    return ResponseModel(message="删除成功")


@router.post("/refresh", response_model=ResponseModel[dict])
async def refresh_portfolio(db: Session = Depends(get_db)):
    return ResponseModel(data=await _build_portfolio_summary(db))


@router.post("/ai-connection-test", response_model=ResponseModel[AiConnectionTestResponse])
async def test_ai_connection(request: AiConnectionTestRequest):
    """测试OpenAI兼容AI接口连通性和延迟。"""
    if not request.base_url.strip() or not request.model.strip() or not request.api_key.strip():
        raise HTTPException(status_code=400, detail="模型名称、Base URL 和 API Key 不能为空")

    try:
        result, latency_ms, status_code = await _call_ai_chat_completion(
            base_url=request.base_url,
            api_key=request.api_key,
            model=request.model,
            timeout=_AI_TEST_TIMEOUT,
            max_tokens=8,
            messages=[{
                "role": "user",
                "content": "只回复 OK，用于接口连通性检测。"
            }],
        )
    except HTTPException:
        raise
    except httpx.TimeoutException as e:
        logger.warning(f"AI接口连通性检测超时: {e}")
        raise HTTPException(status_code=504, detail=f"AI接口连通性检测超时: {str(e)}")
    except httpx.RequestError as e:
        logger.warning(f"AI接口连通性检测失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI接口连通性检测失败: {str(e)}")
    except Exception as e:
        logger.warning(f"AI接口连通性检测异常: {e}")
        raise HTTPException(status_code=502, detail=f"AI接口连通性检测异常: {str(e)}")

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    vision_latency_ms = None
    if request.include_vision:
        try:
            _vision_result, vision_latency_ms, _vision_status_code = await _call_ai_chat_completion(
                base_url=request.base_url,
                api_key=request.api_key,
                model=request.model,
                timeout=_AI_VISION_TEST_TIMEOUT,
                max_tokens=16,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请看这张测试图片，只回复 OK。"},
                        {"type": "image_url", "image_url": {"url": _VISION_TEST_IMAGE_DATA_URL}},
                    ],
                }],
            )
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, str) else str(e.detail)
            raise HTTPException(status_code=e.status_code, detail=f"文本连接成功，但视觉输入测试失败: {detail}")
        except httpx.TimeoutException as e:
            logger.warning(f"AI视觉输入检测超时: {e}")
            raise HTTPException(status_code=504, detail=f"文本连接成功，但视觉输入测试超时: {str(e)}")
        except httpx.RequestError as e:
            logger.warning(f"AI视觉输入检测失败: {e}")
            raise HTTPException(status_code=502, detail=f"文本连接成功，但视觉输入测试失败: {str(e)}")
        except Exception as e:
            logger.warning(f"AI视觉输入检测异常: {e}")
            raise HTTPException(status_code=502, detail=f"文本连接成功，但视觉输入测试异常: {str(e)}")

    message = f"连接成功{f'，模型返回：{content[:40]}' if content else ''}"
    if request.include_vision:
        message = f"{message}；视觉输入测试通过"
    return ResponseModel(data=AiConnectionTestResponse(
        ok=True,
        latency_ms=latency_ms,
        vision_latency_ms=vision_latency_ms,
        status_code=status_code,
        model=request.model,
        message=message
    ))


@router.post("/ai-recognize", response_model=ResponseModel[AiRecognizeResponse])
async def ai_recognize_holding(request: AiRecognizeRequest):
    """AI识别持仓截图，并自动通过数据源匹配基金代码"""
    prompt = request.prompt or DEFAULT_AI_RECOGNIZE_PROMPT

    # 1. 调用 AI 识别图片
    try:
        result, latency_ms, _status_code = await _call_ai_chat_completion(
            base_url=request.base_url,
            api_key=request.api_key,
            model=request.model,
            timeout=_AI_REQUEST_TIMEOUT,
            max_tokens=4096,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": request.image_base64}}
                ]
            }],
        )
        logger.info(f"AI识别接口调用完成: latency={latency_ms}ms model={request.model}")
    except HTTPException:
        raise
    except httpx.TimeoutException as e:
        logger.error(f"AI API调用超时: {e}")
        raise HTTPException(
            status_code=504,
            detail=f"AI截图识别超时: {str(e)}。文本连通性检测只验证普通对话接口；请在设置页勾选视觉输入检测，或换用支持图片输入且响应更快的模型。"
        )
    except httpx.RequestError as e:
        logger.error(f"AI API调用失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI API调用失败: {str(e)}")
    except Exception as e:
        logger.error(f"AI API调用失败: {e}")
        raise HTTPException(status_code=502, detail=f"AI API调用失败: {str(e)}")

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise HTTPException(status_code=502, detail="AI返回内容为空")

    # 2. 解析 AI 返回的 JSON
    json_match = re.search(r'\{[\s\S]*\}', content)
    if not json_match:
        raise HTTPException(status_code=502, detail="AI返回内容中未找到有效的JSON")

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI返回的JSON解析失败: {str(e)}")

    raw_holdings = data.get("holdings", [])
    if not isinstance(raw_holdings, list):
        raise HTTPException(status_code=502, detail="AI返回格式不正确，缺少 holdings 数组")

    expected_count = None
    try:
        raw_expected_count = data.get("expected_count") or data.get("total_count") or data.get("holdings_count")
        expected_count = int(raw_expected_count) if raw_expected_count is not None else None
        if expected_count is not None and expected_count <= 0:
            expected_count = None
    except (TypeError, ValueError):
        expected_count = None

    # 3. 批量通过基金名称匹配基金代码
    from app.services.fund_service import get_fund_service
    fund_service = get_fund_service()

    holdings: list[AiRecognizeHolding] = []
    response_warnings: list[str] = []
    for index, item in enumerate(raw_holdings, start=1):
        if not isinstance(item, dict):
            response_warnings.append(f"第 {index} 条AI结果不是对象，已跳过")
            continue
        try:
            row_index = int(item.get("row_index") or index)
        except (TypeError, ValueError):
            row_index = index
        raw_fund_name = (item.get("raw_fund_name") or item.get("fund_name") or "").strip()
        fund_name = (item.get("fund_name") or raw_fund_name).strip()
        market_value = _to_float(item.get("market_value") or item.get("amount") or item.get("current_value"))
        daily_return = _to_float(item.get("daily_return") or item.get("yesterday_return") or item.get("yesterday_profit"))
        holding_return = _to_float(item.get("holding_return") or item.get("total_return") or item.get("profit"))
        holding_return_rate = item.get("holding_return_rate") or item.get("return_rate") or item.get("profit_rate")
        holding_return_rate_value = None if holding_return_rate is None else _to_float(holding_return_rate, default=0)

        if not fund_name:
            continue

        # 通过名称搜索基金代码
        fund_code = ""
        match_status = "not_found"
        confidence = 0
        match_reason = ""
        warnings: list[str] = []
        candidates: list[dict] = []
        is_truncated_name = any(marker in raw_fund_name or marker in fund_name for marker in ("…", "...", "…)", "(..."))

        if market_value <= 0:
            match_status = "invalid"
            warnings.append("市值为空或小于等于0")
        if market_value > 0 and holding_return >= market_value:
            match_status = "invalid"
            warnings.append("持有收益大于等于市值，反推成本不合理")
        if is_truncated_name:
            warnings.append("基金名称被截断，不能自动导入")

        try:
            if match_status != "invalid":
                _search_keyword, search_results = _search_fund_candidates(fund_service, fund_name, limit=12)
                fund_code, fund_name, match_status, confidence, candidates = _match_fund_candidate(fund_name, search_results)
                match_reason = candidates[0]["reason"] if candidates else ""
                if is_truncated_name and match_status == "matched":
                    fund_code = ""
                    fund_name = raw_fund_name
                    match_status = "ambiguous"
                    confidence = min(confidence, 89)
                    match_reason = "truncated_name"
                if match_status == "ambiguous":
                    warnings.append("基金名称匹配不唯一，需要人工确认")
        except Exception as e:
            logger.warning(f"搜索基金代码失败 [{fund_name}]: {e}")
            warnings.append("基金搜索失败")

        holdings.append(AiRecognizeHolding(
            row_index=row_index,
            fund_code=fund_code,
            fund_name=fund_name,
            raw_fund_name=raw_fund_name,
            market_value=market_value,
            daily_return=daily_return,
            holding_return=holding_return,
            holding_return_rate=holding_return_rate_value,
            match_status=match_status,
            confidence=confidence,
            match_reason=match_reason,
            warnings=warnings,
            candidates=candidates
        ))

    total_value = sum(h.market_value for h in holdings)
    total_return = sum(h.holding_return for h in holdings)
    if expected_count is not None and len(holdings) != expected_count:
        response_warnings.append(f"截图声明持仓 {expected_count} 条，AI返回 {len(holdings)} 条，请核对是否漏识别")

    logger.info(f"AI识别完成: {len(holdings)} 条持仓, 匹配成功 {sum(1 for h in holdings if h.match_status == 'matched')} 条")

    return ResponseModel(data=AiRecognizeResponse(
        holdings=holdings,
        total_value=total_value,
        total_holding_return=total_return,
        holdings_count=len(holdings),
        expected_count=expected_count,
        warnings=response_warnings,
        ai_raw_content=content
    ))
