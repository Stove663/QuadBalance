## Context

`QuadBalance` 已经具备回测、验证、压力测试和策略锁定能力，但当前投资者画像适配结果更偏向“计算结果输出”，而不是“可解释决策输出”。在已有 `strategy-validation` 体系中，`suitable / caution / unsuitable` 只是结论标签；如果不同模块分别拼接解释文本，就容易出现口径不一致、理由缺失或治理提示过度延伸的问题。

本次设计的目标，是把适配结果的解释层收敛为一个统一输出模型，让验证报告、CLI 摘要和策略锁文档共享同一套原因字段和治理语义。

## Goals / Non-Goals

**Goals:**
- 统一适配分类输出的结构，确保每个分类都携带标准化原因。
- 让 `suitable / caution / unsuitable` 的判定理由可读、可审计、可复用。
- 让策略锁文档和验证报告引用同一组解释数据，而不是各自重新生成叙述。
- 明确“分类理由”和“治理动作”之间的边界，避免解释层直接隐含改配建议。
- 保持核心回测与评分逻辑不变，只增强结果表达与归因。

**Non-Goals:**
- 不重写回测引擎或收益计算逻辑。
- 不引入新的外部依赖。
- 不改变既有投资者画像分类的总体规则方向，只规范解释输出。
- 不在此 change 中重构整个报告系统，只处理与适配解释相关的输出链路。

## Decisions

### 1. Use a structured explanation payload for suitability results

适配结果不再只返回单个枚举或自由文本，而是返回一个稳定的结构化对象，至少包含：

- `classification`
- `reasons`
- `drivers`
- `warnings`
- `governance_notes`

这样做的原因是，单一字符串很难同时满足 CLI、CSV、策略锁和人工审阅需求。结构化 payload 更容易在不同输出通道间保持一致。

**Alternatives considered:**
- 只保留枚举分类：最简单，但无法解释原因。
- 返回一长段自然语言：可读性好，但难以复用与测试。
- 结构化对象：略复杂，但最适合稳定集成和审计。

### 2. Separate classification reasons from governance actions

分类结果只回答“为什么是这个等级”，治理信息只回答“看到这个结果后应该怎么处理”。二者必须分栏输出，不允许把 review-required 或 thesis-broken 这类治理语义混进分类定义本身。

这样可以避免一个常见问题：解释文本把“风险提示”写成“策略错误”，从而让用户误以为需要立刻改配。

**Alternatives considered:**
- 将治理规则嵌入分类说明：实现快，但语义混杂。
- 完全分离到不同报告模块：语义清晰，但跨模块维护成本高。
- 同一数据源、两个输出层：兼顾一致性与职责分离。

### 3. Reuse existing validation metrics as explanation drivers

解释层不重新计算指标，而是直接消费验证层已经产生的结果，例如：

- nominal / real annualized return
- maximum drawdown
- rolling real-return failures
- longest underwater duration
- QDII fill rate and weight gap
- lifecycle stress test outcomes

这样可避免重复逻辑和重复口径，减少“验证通过但解释层算出不同结果”的风险。

**Alternatives considered:**
- 在解释层重新计算指标：灵活，但容易分叉。
- 直接读取验证结果：最一致，也最容易测试。

### 4. Standardize explanation granularity by profile

不同画像的解释重点应不同，但字段结构保持一致。例如：

- `accumulation` 更关注长期真实收益、执行摩擦和持续投入体验
- `balanced_core` 更关注回撤、波动和稳定性
- `pre_retirement_preservation` 更关注下行控制、恢复时间和中断情景
- `retirement_withdrawal` 更关注提取压力、耗尽风险和真实购买力

分类逻辑不需要变成“每个画像一套系统”，而是通过相同的解释结构呈现不同画像最关心的指标。

**Alternatives considered:**
- 每个画像独立解释格式：表达贴切，但维护成本高。
- 单一模板覆盖全部画像：一致性好，但容易过于笼统。
- 统一结构 + 画像特定重点字段：最平衡。

### 5. Keep CLI and document rendering as consumers, not decision makers

CLI 与文档层只负责展示和汇总，不负责重新判断分类结论。这样可以确保：

- 回测输出与策略锁文档永远来自同一份解释数据
- 代码的决策逻辑集中在验证/适配层
- 文档渲染不会意外改变结论

**Alternatives considered:**
- 在 CLI 中临时生成解释：开发快，但不可审计。
- 在报告层单独推导：容易和验证层不一致。
- 由验证层生成统一解释 payload：最稳妥。

## Risks / Trade-offs

- [Structured payload makes some call sites more verbose] → Mitigation: provide a small helper or adapter for common display paths.
- [Standardized explanations may feel less flexible] → Mitigation: keep free-text notes inside `reasons` / `warnings` arrays where needed.
- [Different profiles may still require different messaging] → Mitigation: preserve profile-specific emphasis while keeping schema identical.
- [Consumers may continue to rely on old text output] → Mitigation: keep backward-compatible summary rendering during transition.

## Migration Plan

1. Introduce the structured suitability explanation model in the validation/summary layer.
2. Update report rendering to consume the structured payload and emit consistent reasons.
3. Update strategy-lock generation to include the same explanation summary.
4. Adjust CLI summary output to display classification plus top reasons.
5. Validate that current tests and snapshot-like expectations still pass.
6. If needed, keep a compatibility path for any old free-text summary until downstream consumers are migrated.

## Open Questions

- Should the explanation payload be persisted in artifacts, or generated on demand from existing validation results?
- Which fields are mandatory versus optional for each investor profile?
- Should warnings be capped to a small number of top reasons, or can they be fully enumerated?
- Do we want a separate “human review summary” field distinct from the classification reasons?
