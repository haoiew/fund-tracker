## 问题诊断

Redis连接失败的根因是：`FundDataConfig` 类缺少 `REDIS_URL` 属性

### 问题分析

1. **cache_service.py** 从 `app.config` 导入 `fund_config`
2. **config.py** 中 `fund_config = FundDataConfig()`
3. **FundDataConfig** 类没有定义 `REDIS_URL` 属性
4. 当 cache_service 尝试访问 `fund_config.REDIS_URL` 时抛出 AttributeError

### 解决方案

**方案1（推荐）**：在 `FundDataConfig` 类中添加 `REDIS_URL` 属性

修改文件：`d:\workdir\code\Explore\fund-tracker\backend\app\config.py`

```python
# 基金数据配置
class FundDataConfig:
    DEFAULT_FUNDS: List[str] = [...]
    # ... 其他属性 ...
    
    # 添加REDIS_URL配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

### 验证步骤

1. 修改配置后重启后端服务
2. 检查日志中是否显示 "Redis 缓存服务已启用"
3. 如果Redis未运行，可以选择：
   - 安装并启动Redis服务
   - 或保持现状（缓存功能为可选，不影响核心功能）

### 注意事项

- Redis是可选组件，应用可以在无Redis模式下正常运行
- 如需启用缓存，需要安装Redis服务并确保端口6379可访问
- Windows下可通过 WSL、Docker 或直接安装Redis for Windows