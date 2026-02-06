## 问题诊断

终端日志显示两个错误：

1. Redis 连接失败（localhost:6379 拒绝连接）- Redis 服务器未运行
2. `Object of type FundRealtimeData is not JSON serializable` - 这是根本原因

## 根本原因

`cache_service.py` 中的 `PydanticEncoder` 类没有处理 `Decimal` 类型的序列化。`FundRealtimeData` 模型使用了 `Decimal` 字段（estimate\_nav, estimate\_change），导致 JSON 序列化失败。

## 修复方案

修改 `d:\workdir\code\Explore\fund-tracker\backend\app\services\cache_service.py` 中的 `PydanticEncoder` 类，添加对 `Decimal` 类型的支持：

```python
from decimal import Decimal

class PydanticEncoder(json.JSONEncoder):
    """支持 Pydantic 模型的 JSON 编码器"""
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
```

## 可选改进

同时建议添加 `model_dump` 的 mode='json' 参数，让 Pydantic 自动处理 Decimal 转换：

```python
if isinstance(obj, BaseModel):
    return obj.model_dump(mode='json')
```

请确认此修复方案后，我将执行修改。
