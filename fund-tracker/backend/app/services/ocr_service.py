# -*- coding: utf-8 -*-
"""
OCR识别服务 - 截图识别基金持仓
使用 EasyOCR
"""
import re
import base64
import io
import os
from typing import List, Dict, Optional, Tuple
from PIL import Image
from dataclasses import dataclass

from app.config import ocr_config
from app.services.fund_service import fund_service


@dataclass
class ExtractedPosition:
    """提取的持仓数据"""
    fund_name: str
    fund_code: Optional[str]
    market_value: Optional[float]  # 当前市值
    profit_amount: Optional[float]  # 持有收益金额
    profit_rate: Optional[float]  # 持有收益率（小数形式，如0.0582表示5.82%）
    confidence: float


class OcrService:
    """OCR服务类"""

    def __init__(self):
        self.ocr_engine = None
        self._init_ocr()

    def _init_ocr(self):
        """初始化OCR引擎"""
        try:
            import easyocr
            print("正在初始化 EasyOCR...")
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            self.ocr_engine = easyocr.Reader(
                ['ch_sim', 'en'],
                gpu=False,
                download_enabled=True
            )
            print("✅ EasyOCR 初始化成功！")
        except ImportError:
            print("⚠️ EasyOCR 未安装，OCR功能不可用")
            self.ocr_engine = None
        except Exception as e:
            print(f"⚠️ EasyOCR 初始化失败: {str(e)[:100]}")
            self.ocr_engine = None

    def scan_image(self, image_base64: str) -> Dict:
        """扫描图片识别文字"""
        if not self.ocr_engine:
            return {
                "fund_codes": [],
                "fund_names": [],
                "raw_text": "",
                "confidence": 0.0
            }

        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            # 使用临时文件，兼容Windows和Linux
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = tmp.name
            image.save(temp_path)

            result = self.ocr_engine.readtext(temp_path)

            # 清理临时文件
            try:
                os.remove(temp_path)
            except:
                pass

            texts = []
            confidences = []
            for detection in result:
                if len(detection) >= 2:
                    text = detection[1]
                    confidence = detection[2] if len(detection) > 2 else 1.0
                    if confidence > ocr_config.CONFIDENCE_THRESHOLD:
                        texts.append(text)
                        confidences.append(confidence)

            raw_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            fund_codes = self._extract_fund_codes(raw_text)
            fund_names = self._extract_fund_names(raw_text)

            return {
                "fund_codes": fund_codes,
                "fund_names": fund_names,
                "raw_text": raw_text,
                "confidence": avg_confidence,
                "all_texts": texts
            }

        except Exception as e:
            print(f"OCR识别失败: {e}")
            return {
                "fund_codes": [],
                "fund_names": [],
                "raw_text": "",
                "confidence": 0.0,
                "all_texts": []
            }

    def _extract_fund_codes(self, text: str) -> List[str]:
        """从文本中提取基金代码（6位数字）"""
        pattern = ocr_config.FUND_CODE_PATTERN
        matches = re.findall(pattern, text)
        return list(set(matches))

    def _extract_fund_names(self, text: str) -> List[str]:
        """从文本中提取基金名称"""
        # 过滤掉常见非基金名称词汇
        filter_words = ['我的持有', '金额', '昨日收益', '持仓收益', '持有收益', '累计收益',
                        '股票型', '债券型', '混合型', '全部', '交易', '买入', '合计',
                        '基金', '元', '%', '收益率', '收益', '市值', '净值', '份额',
                        '自选', '基金圈', '全球投资', '持仓', '发现', '首页']

        lines = text.split('\n')
        fund_names = []

        for line in lines:
            line = line.strip()
            # 基金名称特征：长度4-30，包含中文，不包含过滤词，不以数字开头
            if (len(line) >= 4 and len(line) <= 30 and
                any('\u4e00' <= c <= '\u9fff' for c in line) and
                not any(fw in line for fw in filter_words) and
                not re.match(r'^\d', line) and
                not re.match(r'^[A-Za-z]+$', line)):  # 不是纯英文
                fund_names.append(line)

        return fund_names

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字（支持千分位逗号）"""
        # 匹配数字，支持逗号分隔和正负号
        match = re.search(r'([+-]?[\d,]+\.?\d*)', text.replace(',', ''))
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None

    def _extract_percentage(self, text: str) -> Optional[float]:
        """从文本中提取百分比并转换为小数"""
        match = re.search(r'([+-]?\d+\.?\d*)\s*%', text)
        if match:
            try:
                return float(match.group(1)) / 100
            except ValueError:
                return None
        return None

    def extract_positions(self, image_base64: str) -> List[ExtractedPosition]:
        """
        从持仓截图中提取持仓数据
        识别基金名称、市值、收益等信息
        """
        scan_result = self.scan_image(image_base64)
        texts = scan_result.get("all_texts", [])
        
        # 调试日志
        print(f"\n{'='*60}")
        print(f"OCR识别到的所有文本 ({len(texts)} 行):")
        for idx, text in enumerate(texts):
            print(f"  [{idx}] {text}")
        print(f"{'='*60}\n")

        positions = []
        i = 0
        while i < len(texts):
            text = texts[i].strip()
            
            # 调试：检查每个文本是否被识别为基金名称
            is_fund = self._is_fund_name(text)
            if is_fund:
                print(f"[识别到基金名称] {text}")

            # 尝试识别基金名称
            if is_fund:
                position = self._parse_position(texts, i)
                if position:
                    print(f"[成功解析持仓] {position.fund_name} - 市值:{position.market_value} 收益:{position.profit_amount}")
                    positions.append(position)
                    # 跳过已处理的行（通常是3-4行：名称、市值、收益、收益率）
                    i += self._get_position_line_count(texts, i)
                    continue
                else:
                    print(f"[解析失败] {text}")

            i += 1
        
        print(f"\n[识别完成] 共识别到 {len(positions)} 只基金\n")

        return positions

    def _is_fund_name(self, text: str) -> bool:
        """判断文本是否是基金名称"""
        # 基金名称特征 - 过滤UI元素
        filter_words = ['我的持有', '金额', '昨日收益', '持仓收益', '持有收益',
                        '累计收益', '全部', '交易', '买入', '合计', '自选', '基金名称',
                        '金额/昨日收益', '持仓收益/率', '近期交易排序', '股票型', '债券型', '混合型']

        # 黑名单：榜单、排名等干扰信息
        blacklist_patterns = [
            r'.*榜\s*No\d+',  # 定投热基榜 No3
            r'.*榜\s*No\.\w+',  # 商品基金榜 No.1
            r'连续跑赢.*',  # 连续跑赢赛道 No5
            r'领涨先锋.*',  # 领涨先锋 No1
            r'.*榜\s*\d+',  # 各种榜单
            r'No\d+.*',  # No开头的排名
        ]

        # 基本长度检查
        if len(text) < 4 or len(text) > 50:
            return False

        # 必须包含中文
        if not any('\u4e00' <= c <= '\u9fff' for c in text):
            return False

        # 过滤掉UI元素文字
        if any(fw in text for fw in filter_words):
            return False

        # 过滤黑名单
        for pattern in blacklist_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False

        # 不以数字或符号开头（除非是基金类型后缀如(QDII)）
        if re.match(r'^\d', text):
            return False
        if re.match(r'^[+-]', text):
            return False

        # 不能是纯英文或纯数字
        if re.match(r'^[A-Za-z]+$', text):
            return False

        # 不能包含明显的非基金名称特征
        if '%' in text:  # 包含百分比的通常是收益率
            return False

        # 基金名称通常包含"基金"、"股票"、"债券"、"混合"、"指数"等关键词
        fund_keywords = ['基金', '股票', '债券', '混合', '指数', 'ETF', 'LOF', 'QDII', '发起', '优选', '精选', '增强', '联接']
        has_fund_keyword = any(kw in text for kw in fund_keywords)

        # 或者包含公司名称
        company_keywords = ['南方', '华夏', '易方达', '嘉实', '博时', '广发', '富国', '鹏华', '汇添富', '工银', '建信', '招商', '中欧', '天弘', '华安', '国泰', '摩根', '永赢', '国投瑞银', '东方红', '银河', '景顺长城', '华宝', '招商中证', '永赢医药', '永赢先进', '永赢高端', '永赢科技']
        has_company_keyword = any(kw in text for kw in company_keywords)

        # 如果既没有基金关键词也没有公司关键词，可能是普通文字
        if not has_fund_keyword and not has_company_keyword:
            # 但如果是较长的中文文本，也可能是基金名称
            if len(text) < 8:
                return False

        return True

    def _parse_position(self, texts: List[str], start_idx: int) -> Optional[ExtractedPosition]:
        """解析持仓数据（从基金名称开始的多行）"""
        fund_name_parts = [texts[start_idx].strip()]
        print(f"  [解析] 基金名称(起始): {fund_name_parts[0]}")

        market_value = None
        profit_amount = None
        profit_rate = None
        confidence = 0.8

        # 向后查找相关数据（通常在下1-6行）
        end_idx = min(start_idx + 7, len(texts))
        print(f"  [解析] 查找范围: 行{start_idx+1} 到 行{end_idx}")

        j = start_idx + 1
        while j < end_idx:
            text = texts[j].strip()
            print(f"    检查行[{j}]: {text}")

            # 检查是否是基金类型后缀（如(QDII-LOF)、联接C等）
            # 这些应该合并到基金名称中
            if self._is_fund_type_suffix(text):
                print(f"      -> 识别为基金类型后缀，合并到名称")
                fund_name_parts.append(text)
                j += 1
                continue

            # 如果遇到下一个基金名称，停止
            if self._is_fund_name(text):
                print(f"      -> 遇到下一个基金名称，停止")
                break

            # 提取市值（通常是较大的正数，带千分位）
            if market_value is None:
                num = self._extract_number(text)
                print(f"      -> 提取数字: {num}")
                # 市值特征：通常是正数，且大于50，不带正负号前缀（除非是纯数字）
                if num and num > 50:
                    # 检查原始文本是否以+或-开头（如果是，可能是收益而非市值）
                    original_text = texts[j].strip()
                    if original_text.startswith('+') or original_text.startswith('-'):
                        # 如果是带符号的数字，可能是收益，先跳过，后续再判断
                        if profit_amount is None:
                            profit_amount = num
                            print(f"      -> 识别为收益(带符号): {profit_amount}")
                            j += 1
                            continue
                    else:
                        market_value = num
                        print(f"      -> 识别为市值: {market_value}")
                        j += 1
                        continue

            # 提取收益金额（带正负号）
            if profit_amount is None:
                num = self._extract_number(text)
                if num is not None and abs(num) < 50000:  # 收益金额范围
                    profit_amount = num
                    print(f"      -> 识别为收益: {profit_amount}")
                    j += 1
                    continue

            # 提取收益率（带%）
            if profit_rate is None:
                rate = self._extract_percentage(text)
                if rate is not None:
                    profit_rate = rate
                    print(f"      -> 识别为收益率: {profit_rate}")
                    j += 1
                    continue

            # 其他情况，跳过
            j += 1

        # 合并基金名称
        fund_name = ' '.join(fund_name_parts)

        # 修复OCR识别错误：QDIILOF -> QDII-LOF, QDIIFOFC -> QDII-FOF-C 等
        fund_name = self._fix_ocr_errors(fund_name)

        print(f"  [解析] 合并后基金名称: {fund_name}")

        # 如果没有找到市值，可能不是有效的持仓行
        if market_value is None:
            print(f"  [解析失败] 未找到市值")
            return None

        print(f"  [解析成功] 市值:{market_value} 收益:{profit_amount} 收益率:{profit_rate}")
        return ExtractedPosition(
            fund_name=fund_name,
            fund_code=None,  # 后续通过名称匹配
            market_value=market_value,
            profit_amount=profit_amount,
            profit_rate=profit_rate,
            confidence=confidence
        )

    def _is_fund_type_suffix(self, text: str) -> bool:
        """判断文本是否是基金类型后缀（如QDII-LOF、联接C等）"""
        # 基金类型后缀特征
        suffix_patterns = [
            r'^\(QDII.*\)$',  # (QDII-LOF)、(QDII-FOF)等
            r'^\(LOF\)[A-Z]$',  # (LOF)A、(LOF)C
            r'^\(FOF\).*$',  # (FOF)相关
            r'^联接[ABC]$',  # 联接A、联接C
            r'^指数[ABC]$',  # 指数A、指数C
            r'^[ABC]$',  # 单独的A、B、C份额标识
        ]

        for pattern in suffix_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        # 如果文本很短（1-10字符），且包含基金类型关键词，也可能是后缀
        if len(text) <= 10:
            type_keywords = ['QDII', 'LOF', 'FOF', 'ETF', '联接', '指数']
            if any(kw in text for kw in type_keywords):
                return True

        return False

    def _fix_ocr_errors(self, text: str) -> str:
        """修复OCR识别中的常见错误"""
        # QDII相关修复
        text = re.sub(r'QDIILOF', 'QDII-LOF', text, flags=re.IGNORECASE)
        text = re.sub(r'QDII-LOF', 'QDII-LOF', text, flags=re.IGNORECASE)
        text = re.sub(r'\(QDIILOF\)', '(QDII-LOF)', text, flags=re.IGNORECASE)
        text = re.sub(r'\(QDII([^-])', r'(QDII-\1', text, flags=re.IGNORECASE)

        # 其他常见OCR错误修复
        text = re.sub(r'夭弘', '天弘', text)  # 夭 -> 天
        text = re.sub(r'华室', '华宝', text)  # 室 -> 宝
        text = re.sub(r'那华', '鹏华', text)  # 那 -> 鹏

        return text

    def _get_position_line_count(self, texts: List[str], start_idx: int) -> int:
        """获取一个持仓条目占用的行数"""
        count = 1  # 基金名称行

        for j in range(start_idx + 1, min(start_idx + 5, len(texts))):
            text = texts[j].strip()

            # 如果遇到下一个基金名称，停止
            if self._is_fund_name(text):
                break

            # 如果遇到明显的分隔标志，停止
            if text in ['我的持有', '全部']:
                break

            count += 1

        return count

    def match_fund_by_name(self, fund_name: str) -> Optional[Dict]:
        """通过基金名称匹配基金代码"""
        try:
            # 搜索基金
            search_results = fund_service.search_funds(fund_name, limit=5)

            if not search_results:
                return None

            # 返回最佳匹配
            best_match = search_results[0]

            # 计算名称相似度（简单实现）
            similarity = self._calculate_similarity(fund_name, best_match.get('name', ''))

            return {
                "code": best_match.get('code'),
                "name": best_match.get('name'),
                "similarity": similarity
            }

        except Exception as e:
            print(f"基金匹配失败: {e}")
            return None

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """计算两个基金名称的相似度"""
        # 简单实现：计算共同字符比例
        set1 = set(name1)
        set2 = set(name2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def calculate_position_details(self, position: ExtractedPosition) -> Dict:
        """
        计算持仓详情
        根据市值和收益率计算份额、成本净值等
        """
        result = {
            "fund_name": position.fund_name,
            "fund_code": position.fund_code,
            "market_value": position.market_value,
            "profit_amount": position.profit_amount,
            "profit_rate": position.profit_rate,
            "confidence": position.confidence,
            # 需要计算的字段
            "hold_shares": None,
            "cost_nav": None,
            "current_nav": None
        }

        # 如果有收益率，可以计算成本净值关系
        if position.profit_rate is not None and position.profit_rate != 0:
            # 收益率 = (当前市值 - 成本) / 成本
            # 成本 = 当前市值 / (1 + 收益率)
            cost = position.market_value / (1 + position.profit_rate)
            result["cost_basis"] = round(cost, 2)

        return result

    def process_screenshot(self, image_base64: str, calculate_details: bool = True) -> Dict:
        """
        处理持仓截图：识别、匹配、计算完整数据
        
        Args:
            image_base64: 图片base64编码
            calculate_details: 是否计算详细的持仓数据（份额、成本等）
        """
        # 1. 提取持仓数据
        positions = self.extract_positions(image_base64)

        if not positions:
            return {
                "positions": [],
                "total_count": 0,
                "matched_count": 0,
                "raw_result": self.scan_image(image_base64)
            }

        # 2. 匹配基金代码
        matched_positions = []
        fund_codes_to_fetch = []
        
        for pos in positions:
            matched_fund = self.match_fund_by_name(pos.fund_name)

            if matched_fund:
                pos.fund_code = matched_fund["code"]
                pos.confidence = matched_fund.get("similarity", 0.8)
                if pos.fund_code:
                    fund_codes_to_fetch.append(pos.fund_code)

            matched_positions.append(pos)

        # 3. 如果需要，获取最新净值并计算详细数据
        if calculate_details and fund_codes_to_fetch:
            try:
                from app.services.fund_core_service import fund_core_service
                nav_data_list = fund_core_service.get_realtime_batch(fund_codes_to_fetch)
                nav_data = {d.code: d for d in nav_data_list}
            except Exception as e:
                print(f"获取净值数据失败: {e}")
                nav_data = {}
        else:
            nav_data = {}

        # 4. 构建返回结果
        result_positions = []
        for pos in matched_positions:
            details = self.calculate_position_details(pos)
            
            # 如果有基金代码和市值，计算份额和成本
            if pos.fund_code and pos.market_value and calculate_details:
                nav_info = nav_data.get(pos.fund_code)
                if nav_info and nav_info.estimate_nav:
                    latest_nav = float(nav_info.estimate_nav)
                    
                    # 计算份额 = 市值 / 最新净值
                    hold_shares = pos.market_value / latest_nav
                    details["hold_shares"] = round(hold_shares, 2)
                    details["current_nav"] = latest_nav
                    
                    # 计算成本数据
                    if pos.profit_amount is not None:
                        # 成本金额 = 市值 - 收益
                        cost_amount = pos.market_value - pos.profit_amount
                        details["cost_amount"] = round(cost_amount, 2)
                        
                        # 成本价 = 成本金额 / 份额
                        if hold_shares > 0:
                            cost_nav = cost_amount / hold_shares
                            details["cost_nav"] = round(cost_nav, 4)
            
            result_positions.append(details)

        return {
            "positions": result_positions,
            "total_count": len(positions),
            "matched_count": len([p for p in result_positions if p["fund_code"]]),
            "raw_result": {
                "fund_codes": [p["fund_code"] for p in result_positions if p["fund_code"]],
                "fund_names": [p["fund_name"] for p in result_positions],
                "raw_text": "",
                "confidence": sum(p["confidence"] for p in result_positions) / len(result_positions) if result_positions else 0
            }
        }

    def match_funds(self, extracted_texts: List[str]) -> List[Dict]:
        """匹配识别到的基金（兼容旧接口）"""
        matches = []

        for text in extracted_texts:
            if re.match(r'^\d{6}$', text):
                try:
                    fund_name = fund_service.get_fund_name(text)
                    if fund_name != text:
                        matches.append({
                            "extracted_text": text,
                            "matched_fund": {"code": text, "name": fund_name},
                            "confidence": 1.0
                        })
                        continue
                except:
                    pass

            search_results = fund_service.search_funds(text, limit=1)
            if search_results:
                matches.append({
                    "extracted_text": text,
                    "matched_fund": search_results[0],
                    "confidence": 0.8
                })
            else:
                matches.append({
                    "extracted_text": text,
                    "matched_fund": None,
                    "confidence": 0.0
                })

        return matches


ocr_service = OcrService()
