## Context

实现 `openspec/specs/` 中已锁定的策略与验证需求。数据源使用 akshare（东方财富 ETF 日线），回测框架基于 pandas 向量化 + 事件驱动再平衡。

## Goals / Non-Goals

**Goals:**

- 完整实现 strategy-validation spec 中的回测、扫描、压力测试、验收标准
- 可复现的 CLI：`uv run portfolio-backtest`
- 本地缓存 ETF 数据，避免重复请求

**Non-Goals:**

- 券商 API、实时行情、自动化交易
- Web UI 或数据库持久化
- 场外货币基金

## Decisions

### D1: 项目结构

```
src/permanent_portfolio/
  config.py       # 标的、比例变体、扫描参数
  data.py         # akshare 获取 + parquet 缓存
  simulator.py    # 组合模拟核心
  metrics.py      # 收益、波动、回撤、夏普
  benchmarks.py   # 三基准对比
  stress.py       # S1-S6 压力测试
  validation.py   # 验收判定 + lock 文档
  sweep.py        # 参数扫描编排
  cli.py          # 入口
```

### D2: 模拟器设计

- 按交易日遍历，维护各标的份额
- 每月首个交易日执行定投
- 每年首个交易日检查再平衡（±threshold）
- 交易成本默认双边 0.1%
- 组合净值 = Σ(shares × price)

### D3: 数据获取

使用 `akshare.fund_etf_hist_em(symbol, period="daily")` 获取前复权收盘价。

### D4: 压力测试实现

在历史回测路径上叠加冲击：修改特定年份各象限收益率，重算组合影响；S5 在买入 513500 时加 5% 溢价。

### D5: 输出

- `output/sweep_results.csv` — 所有配置指标
- `output/strategy-lock.md` — 首个通过验收的配置（若有）

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| akshare API 变更 | 封装 data 层，缓存 parquet |
| 长回测性能 | 向量化净值计算，扫描可并行（后续） |
| QDII 数据起始日晚 | spec 要求按标的实际起始日模拟 |

## Open Questions

- 并行扫描 — v1 串行即可
