## Why

当前的 `profile suitability` 已经有分类结果，但不同模块对“为什么是 suitable / caution / unsuitable”的解释可能不一致，导致策略锁、治理提示和回测报告之间的可读性与可审计性不够统一。现在把解释逻辑收敛成一个明确能力，可以减少决策歧义，并让画像适配结果更适合作为后续策略锁定与人工复核的依据。

## What Changes

- 统一投资者画像适配结果的输出结构，明确每个分类必须附带可读原因。
- 标准化 `suitable / caution / unsuitable` 的解释维度，确保回测、验证和策略锁文档使用同一套说明口径。
- 增加对关键驱动因子的摘要输出，例如收益、回撤、滚动真实收益、执行摩擦、生命周期压力测试结果。
- 明确治理触发信息与适配分类之间的边界，避免把“需要复核”误解为自动改配。
- 让策略锁选择过程更容易说明“为什么选中这个配置”，尤其在多个候选都通过验证时。

## Capabilities

### New Capabilities
- `suitability-explainability`: 定义投资者画像适配结果的解释性输出、原因摘要和治理提示格式。

### Modified Capabilities
- `investment-strategy`: 策略适配与锁定流程需要采用统一的解释性输出，并在报告中呈现原因摘要。
- `strategy-validation`: 适配性结果输出需要更一致的分类原因字段，以支持验证报告和策略锁文档。

## Impact

- 影响验证报告与策略锁文档的内容结构。
- 影响 `quadbalance` CLI 的结果展示与报告生成流程。
- 可能涉及 `validation.py`、`reporting.py`、`reporting_sections.py`、`cli.py` 等输出层代码。
- 不改变核心回测数值逻辑，主要影响结果表达、归因和治理可读性。
