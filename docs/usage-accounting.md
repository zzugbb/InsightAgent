# 任务与会话用量汇总

## 统一口径

任务/会话 summary、Usage Dashboard 的汇总/趋势/会话榜/任务榜、会话导出中的 usage_summary，以及前端 Context Inspector 的会话汇总，均统计规划（含后续反馈决策）与最终回答的已记录用量。

- 每个 prompt_tokens、completion_tokens、cost_estimate 字段优先读取有效的 `overall_*`，不再叠加 planning，避免重复计数。
- 某个 overall 字段缺失或无效时，分别将已知的最终回答字段与 `planning_*` 相加；只有一个已知值时保留该值，均未知时保持未知。旧任务仅有最终回答字段时沿用原值。
- 有效值为有限、非负数字或可解析的数字字符串；0 是有效值。bool、负数、空白、NaN/Infinity 不进入汇总，也不产生新的估算。
- 汇总 total_tokens 为汇总 prompt + completion，保留原统计定义；不是从上游账单读取。cost_estimate 仍使用项目已配置单价的估算值。
- 来源分布与 source_kind 筛选包含已有规划来源：已记录 provider 与 estimated 混用时归为 mixed；无法判断的参与阶段保留 legacy。任务原始 final/planning/overall 明细字段与 API/SSE/Trace/export 形状不变。

汇总依据持久化 usage_json。执行器失败或超时终结时保存已记录的规划/决策用量；最终生成已完成时保留正常用量记录，否则只读取该次最终调用实际返回的 ProviderUsage，缺失字段保持未知，不根据部分文本推算未完成调用的消耗。只有总量时保留 provider_total_tokens，不反推输入/输出；不将上一轮规划的 last_usage 当作最终回答用量。历史缺失记录不回填，已由外部取消或其他实例终结的任务不覆盖；没有持久化用量仍不能证明没有上游消耗。

首次或后续规划的模型响应已收到、但依赖图校验失败时，规划器仅随原图错误传递该次 ProviderUsage，执行器在失败保存前计入 planning。错误正文、原始计划不进入新增用量记录，也不回退执行非法图。只有 prompt/completion 都已知时才计算该次 total 和成本；多次规划任一字段未知时，该字段合计保持未知，上游 provider_total_tokens 仍独立累计。无有效用量仅保留此前已记录值；最终回答未启动时不生成 final 用量。

非流式请求开始前重置 last_usage；空正文错误仅携带该次响应实际返回的用量，不读取上一请求残留。首轮失败保留原规则回退，Trace 与任务用量只保存有效字段；后续规划失败仍终结任务并计入当前消耗。最终成功汇总复用失败保存的字段规则，不把部分 planning 字段转成 0；overall 继续统计各阶段已知字段，不宣称未知消耗不存在。

前端详情/Context Inspector 支持仅 planning/overall 的记录：规划与汇总可见，最终回答字段显示未知；会话聚合仍按已知字段计算。

实现位置：后端 `app/services/usage_accounting.py` 提供统一读取规则，持久化 facade 与仪表盘复用；前端 `workbench/utils.ts` 的会话聚合使用同一读取顺序，当前任务仍展示 final/planning/overall 明细。

## 验证与维护

历史用量汇总 PostgreSQL 3/3 核对多轮 summary/dashboard/导出，后续规划反馈 20/20 覆盖空正文、非法图与 429 的完整/部分/缺失用量；均为本地 Provider/HTTP 替身。最新完整门禁见[验证基线](validation-baseline.md)。

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k usage_accounting
backend/.venv/bin/python backend/scripts/test_usage_accounting_postgres.py
cd frontend
node --test --experimental-strip-types app/components/workbench/usage-accounting.node.test.ts
```


专项已纳入静态门禁与 backend-e2e；真实供应商已记录用量、放弃规划的未知消耗与账单边界见[真实模型验收](real-model-acceptance.md)。
