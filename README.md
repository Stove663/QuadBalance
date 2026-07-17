# QuadBalance

QuadBalance 是一个面向中国市场的四象限组合回测与验证引擎，适合用于长期资产配置研究、压力测试、适配性校验和报告生成。

## 一页式摘要

- **组合结构**：股票 / 债券 / 黄金 / 现金
- **默认模板**：`25-25-25-25`
- **股票拆分**：国内股票 60% / QDII 海外股票 40%
- **默认 QDII 目标权重**：约 10%
- **主要能力**：回测、压力测试、风险地图、lock document

## 投资组合基本情况

| 象限 | 角色 | 典型工具 |
|------|------|----------|
| Stocks（股票） | 提供长期增长 | 国内股票基金 + QDII 海外股票基金 |
| Bonds（债券） | 提供稳定性 | 中短久期国债/政金债基金或同类替代 |
| Gold（黄金） | 提供分散化与尾部对冲 | 黄金基金 |
| Cash（现金） | 提供流动性与缓冲 | 货币基金/现金管理工具 |

### 默认配置

| 配置项 | 默认值 |
|--------|--------|
| Allocation template | `25-25-25-25` |
| Bond variant | `B1` |
| DCA method | `proportional` |
| Rebalance threshold | `5%` |
| Stock sub split | `60-40` |
| QDII daily caps | 启用 |

### 可选模板

- `25-25-25-25`
- `20-30-25-25`
- `30-20-25-25`
- `20-25-30-25`
- `35-20-20-25`
- `40-20-20-20`
- `45-20-20-15`
- `50-20-15-15`
- `30-25-20-25`
- `20-30-20-30`
- `15-35-15-35`

### 股票与债券拆分

- 股票子拆分：`60-40`、`50-50`、`40-60`
- 债券 variant：`B1`、`B2`、`B3`

## 如何理解这套组合的风险

这套组合追求的是长期平衡，而不是每年都上涨。

### 主要风险

- **股票**：增长强，但回撤也最大
- **债券**：通常更稳，但在利率上行或流动性紧张时也会承压
- **黄金**：用于分散和尾部对冲，但不保证上涨
- **现金**：提供流动性，但长期可能跑不赢通胀
- **路径风险**：同样的最终涨跌，先跌后涨和先涨后跌结果不同
- **执行风险**：再平衡摩擦、QDII 额度、赎回延迟、跨境约束等

### 这套组合最怕什么

- 股票和债券同时承压
- 黄金未能发挥对冲作用
- 现金真实收益为负且通胀持续偏高
- 再平衡在关键时点失效
- QDII 配置受额度、溢价或跨境约束影响
- 投资者在深度回撤后中断定投或改变策略

## 输入 / 输出

### 输入

- 历史价格矩阵
- 策略配置（权重、债券 variant、再平衡阈值、DCA 方式）
- 投资者画像或阈值覆盖
- 代理数据 / 起始日期 / 缺失数据补齐规则

### 输出

- 组合净值序列
- 年度象限收益
- 绩效指标
- 压力测试结果
- 风险地图摘要
- lock document / 报告文件

## 示例命令

```bash
uv sync
uv run quadbalance --help
uv run pytest
uv run quadbalance --output output
```

## 示例输出

```text
Loading data and running parameter sweep...

Sweep complete: 12/36 configurations passed validation
Results written to output/sweep_results.csv
Strategy lock document: output/strategy-lock.md
Locked configuration: 25-25-25-25_B1_prop_5pct_s60-40
Run artifacts: output/artifacts
Proxy sensitivity: output/proxy_sensitivity.csv
Segment metrics: output/segment_metrics.csv
```

## 当前压力测试覆盖

- 市场价格与相关性压力
- 长期宏观与购买力压力
- 动态路径压力
- 行为规则压力
- 跨境访问与结算约束压力
- 产品层实现风险评分
- 回撤痛苦指标（Ulcer Index、Pain Index、CDaR）

## 快速开始

```bash
uv sync
uv run quadbalance --help
uv run pytest
uv run quadbalance --output output
```

## 环境要求

- Python 3.14 或更高版本
- 推荐通过 `uv` 管理依赖和运行环境

## 项目定位

- 面向中国资产市场的组合回测与验证
- 支持投资者画像、资产配置与适配性校验
- 提供策略扫描、指标计算、压力测试与报告输出
- 适合作为研究、策略验证和组合管理的实验平台

## 目录说明

- `src/quadbalance/`：核心实现
- `tests/`：测试用例
- `openspec/`：需求、设计和任务说明

## 说明

本项目当前处于持续演进阶段，README 会随着功能完善持续补充。
