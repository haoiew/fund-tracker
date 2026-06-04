# -*- coding: utf-8 -*-
"""
自维护东方财富API数据源适配器
直接调用东方财富/天天基金/腾讯等底层API
无第三方金融数据库依赖
"""
import json
import time
import re
from typing import List, Optional, Dict
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import BaseDataSource, FundDataResult


class EastmoneyApiSource(BaseDataSource):
    """自维护东方财富API数据源"""

    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })

    def get_name(self) -> str:
        return "eastmoney_direct"

    def fetch_single(self, code: str) -> FundDataResult:
        """获取单只基金数据 - 多策略降级"""
        start = time.time()

        # 策略1: 天天基金实时估值
        result = self._try_tiantian(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略2: 腾讯基金接口
        result = self._try_tencent(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略3: 东方财富历史净值API (JSON格式，更可靠)
        result = self._try_eastmoney_lsjz(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        # 策略4: 东方财富pingzhongdata JS解析
        result = self._try_eastmoney_pingzhongdata(code)
        if result.is_success:
            result.fetch_duration_ms = (time.time() - start) * 1000
            return result

        duration = (time.time() - start) * 1000
        return self._create_error_result(code, "所有策略均失败", duration)

    def _try_tiantian(self, code: str) -> FundDataResult:
        """天天基金实时估值API"""
        try:
            ts = int(time.time() * 1000)
            url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={ts}"
            resp = self.session.get(url, timeout=5)

            if resp.status_code == 200 and resp.text:
                text = resp.text.replace("jsonpgz(", "").replace(");", "").strip()
                if text:
                    data = json.loads(text)
                    name = data.get('name', code)
                    gz = data.get('gsz')
                    gszzl = data.get('gszzl')

                    if gz and float(gz) > 0:
                        return self._create_success_result(
                            code=code,
                            name=name,
                            nav=float(gz),
                            change_pct=float(gszzl) if gszzl else None,
                            update_time=data.get('gztime'),
                            raw_data={'source': '天天基金', **data},
                            duration_ms=0
                        )
        except Exception:
            pass
        return self._create_error_result(code, "天天基金失败", 0)

    def _try_tencent(self, code: str) -> FundDataResult:
        """腾讯基金接口"""
        try:
            url = f"http://qt.gtimg.cn/q=jj{code}"
            resp = self.session.get(url, timeout=3)

            if resp.status_code == 200 and "v_jj" in resp.text:
                content = resp.text.split('="')[1].strip('";\n')
                parts = content.split('~')

                if len(parts) > 8:
                    name = parts[1] if parts[1] else code
                    price_str = parts[2].strip() if parts[2] else ''
                    nav_str = parts[5].strip() if len(parts) > 5 and parts[5] else ''
                    change_str = parts[7].strip() if len(parts) > 7 and parts[7] else ''

                    nav = None
                    if price_str and price_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            nav = float(price_str)
                        except ValueError:
                            pass
                    elif nav_str and nav_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            nav = float(nav_str)
                        except ValueError:
                            pass

                    change_pct = None
                    if change_str and change_str not in ['0.00', '0.0000', '0', '']:
                        try:
                            change_pct = float(change_str)
                        except ValueError:
                            pass

                    if nav is not None or change_pct is not None:
                        update_time = parts[8] if len(parts) > 8 else datetime.now().strftime('%H:%M:%S')
                        return self._create_success_result(
                            code=code,
                            name=name,
                            nav=nav,
                            change_pct=change_pct,
                            update_time=update_time,
                            raw_data={'source': '腾讯基金'},
                            duration_ms=0
                        )
        except Exception:
            pass
        return self._create_error_result(code, "腾讯基金失败", 0)

    def _try_eastmoney_lsjz(self, code: str) -> FundDataResult:
        """东方财富历史净值API - JSON格式，更可靠"""
        try:
            url = f"http://api.fund.eastmoney.com/f10/lsjz"
            params = {
                'fundCode': code,
                'pageIndex': 1,
                'pageSize': 1
            }
            headers = {
                'Referer': f'http://fund.eastmoney.com/{code}.html'
            }
            resp = self.session.get(url, params=params, headers=headers, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                if data.get('Data') and data['Data'].get('LSJZList'):
                    items = data['Data']['LSJZList']
                    if items:
                        latest = items[0]
                        nav = float(latest.get('DWJZ', 0))
                        if nav > 0:
                            return self._create_success_result(
                                code=code,
                                name=data['Data'].get('SHORTNAME', code),
                                nav=nav,
                                change_pct=float(latest.get('JZZZL', 0)) if latest.get('JZZZL') else None,
                                update_time=latest.get('FSRQ'),
                                raw_data={'source': '东方财富lsjz', **latest},
                                duration_ms=0
                            )
        except Exception:
            pass
        return self._create_error_result(code, "东方财富lsjz失败", 0)

    def _try_eastmoney_pingzhongdata(self, code: str) -> FundDataResult:
        """东方财富pingzhongdata JS解析"""
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=5)

            if resp.status_code == 200:
                content = resp.text

                # 提取净值历史数据
                match = re.search(r'var Data_netWorthTrend = (\[.*?\]);', content, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    if len(data) >= 1:
                        latest = data[-1]
                        nav = latest.get('y')

                        # 计算涨跌幅
                        change_pct = None
                        if len(data) >= 2:
                            prev = data[-2]
                            prev_val = prev.get('y', 0)
                            if prev_val > 0:
                                change_pct = round((nav - prev_val) / prev_val * 100, 2)

                        if nav and nav > 0:
                            # 解析时间戳
                            update_time = None
                            if latest.get('x'):
                                try:
                                    update_time = datetime.fromtimestamp(latest['x'] / 1000).strftime('%Y-%m-%d')
                                except:
                                    pass

                            return self._create_success_result(
                                code=code,
                                name=code,
                                nav=nav,
                                change_pct=change_pct,
                                update_time=update_time,
                                raw_data={'source': '东方财富pingzhongdata'},
                                duration_ms=0
                            )
        except Exception:
            pass
        return self._create_error_result(code, "东方财富pingzhongdata失败", 0)

    def fetch_batch(self, codes: List[str]) -> List[FundDataResult]:
        """批量获取 - 串行调用"""
        return [self.fetch_single(c) for c in codes]
