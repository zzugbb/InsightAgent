# 任务与会话用量汇总

## 统一口径

任务/会话 summary、Usage Dashboard 的汇总/趋势/会话榜/任务榜、会话导出中的 usage_summary，以及前端 Context Inspector 的会话汇总，均统计规划（含后续反馈决策）与最终回答的已记录用量。

- 每个 prompt_tokens、completion_tokens、cost_estimate 字段优先读取有效的 `overall_*`，不再叠加 planning，避免重复计数。
- 某个 overall 字段缺失或无效时，分别将已知的最终回答字段与 `planning_*` 相加；只有一个已知值时保留该值，均未知时保持未知。旧任务仅有最终回答字段时沿用原值。
- 有效值为有限、非负数字或可解析的数字字符串；0 是有效值。bool、负数、空白、NaN/Infinity 不进入汇总，也不产生新的估算。
- 汇总 total_tokens 为汇总 prompt + completion，保留原统计定义；不是从上游账单读取。cost_estimate 仍使用项目已配置单价的估算值。
- 来源分布与 source_kind 筛选包含已有规划来源：已记录 provider 与 estimated 混用时归为 mixed；无法判断的参与阶段保留 legacy。任务原始 final/planning/overall 明细字段与 API/SSE/Trace/export 形状不变。

汇总依据持久化 usage_json；没有持久化用量的失败或中断任务不能据此证明没有发生上游消耗。此修复不补造缺失记录。

实现位置：后端 `app/services/usage_accounting.py` 提供统一读取规则，持久化 facade 与仪表盘复用；前端 `workbench/utils.ts` 的会话聚合使用同一读取顺序，当前任务仍展示 final/planning/overall 明细。

## 验证与维护

```bash
backend/.venv/bin/python backend/scripts/test_tool_runtime_slice.py -k usage_accounting
backend/.venv/bin/python backend/scripts/test_usage_accounting_postgres.py
cd frontend
node --test --experimental-strip-types app/components/workbench/usage-accounting.node.test.ts
```

2026-10-08：后端静态 8/8、前端计算 6/6、独立 PostgreSQL 集成 3/3。真实任务的三次规划/决策共 36 token，回答 35 token，SSE/任务明细/汇总/趋势/排行榜/会话导出均按 71 token 对齐；另覆盖混合来源筛选、旧数据回退、排名与用户隔离。模型为本地替身。新专项已进入静态 release gate 与 backend-e2e。

验证来源：`/tmp/insightagent-usage-accounting-{static,frontend,postgres}.log`；完整门禁 `/tmp/insightagent-usage-accounting-release.md` / `.json`（10/10 PASS、后端 2175/2175、前端 206/206）。本轮未重跑浏览器或真实模型。
