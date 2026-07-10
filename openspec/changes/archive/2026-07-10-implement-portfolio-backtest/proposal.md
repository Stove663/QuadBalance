## Why

策略规格（investment-strategy、asset-universe、strategy-validation）已固化，但尚无代码验证候选配置是否满足验收标准。需要实现 Python 回测引擎，对参数空间进行扫描，运行压力测试，并为通过验收的配置生成策略锁定文档。

## What Changes

- 使用 uv 初始化 Python 项目，依赖 akshare、pandas、numpy
- 实现 ETF 历史数据获取与本地缓存
- 实现组合模拟器：底仓、比例定投、年度再平衡
- 实现参数扫描、核心指标、基准对比、压力测试、验收判定
- 提供 CLI 入口运行完整验证流程并输出 strategy-lock.md

## Capabilities

### New Capabilities

- `portfolio-backtest`: 回测引擎、数据层、模拟器、指标计算、压力测试、策略锁定文档生成

### Modified Capabilities

（无——实现已有 strategy-validation 等 spec 的需求，不改变 spec 行为）

## Impact

- 新增 `src/permanent_portfolio/` Python 包
- 新增 `pyproject.toml`、`tests/`
- 运行时依赖 akshare 网络获取 ETF 数据
- 输出 `output/` 目录下的回测报告与 strategy-lock.md
