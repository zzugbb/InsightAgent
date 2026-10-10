export type ArchitectureModule = {
  title: string;
  subtitle: string;
  description: string;
  boundary: string;
  source: string;
};

export const executionModules: Record<string, ArchitectureModule> = {
  input: {
    title: "任务输入",
    subtitle: "Input · 工作台",
    description:
      "工作台提交问题，后端创建任务；前端通过 SSE 接管执行并接收 Trace 与回答。",
    boundary: "仅创建任务不保证离开客户端后仍自动执行。",
    source: "docs/runtime-contracts.md",
  },
  planner: {
    title: "模型规划",
    subtitle: "Planner · 结构化计划",
    description:
      "模型结合当前问题、同会话上下文和可用工具生成计划，后端校验计划与依赖。",
    boundary: "展示的是结构化计划与公开执行记录，不展示模型内部思维。",
    source: "docs/architecture.md",
  },
  executor: {
    title: "工具执行",
    subtitle: "Executor · 受控调度",
    description:
      "执行器根据已校验的计划调度工具，绑定前序结果，记录真实输入、输出与状态。",
    boundary: "受队列、轮次、节点数、取消与超时约束；不是任意代码执行环境。",
    source: "docs/tool-execution.md",
  },
  decision: {
    title: "反馈决策",
    subtitle: "Feedback · 有界循环",
    description:
      "每轮工具结果整理为安全观测，模型决定继续调用工具还是进入最终回答。",
    boundary: "循环有执行上限；反馈可能失败或超时；失败记录继续保留。",
    source: "docs/architecture.md#agent-上下文与反馈",
  },
  answer: {
    title: "流式回答",
    subtitle: "Answer · SSE",
    description:
      "模型根据问题、计划和实际工具结果生成最终回答，后端通过 SSE 将文本流送到工作台。",
    boundary: "回答仍需核对执行与引用证据；流结束不等于目标全部满足。",
    source: "docs/runtime-contracts.md#流结束与回答完整性",
  },
  commit: {
    title: "保存结果",
    subtitle: "Commit · 业务账本",
    description:
      "成功状态、最终 Trace、用量和回答在同一 PostgreSQL 事务提交，之后发送 done。",
    boundary:
      "成功提交后的 Memory 摘要为尽力写入；写入失败不会反转已完成任务。",
    source: "docs/runtime-contracts.md#成功提交与终态竞争",
  },
  retrieve: {
    title: "知识检索",
    subtitle: "task_retrieve · RAG",
    description:
      "检索目标知识库，返回可复核的来源、文档版本与命中片段，供后续工具或回答使用。",
    boundary: "是否检索由任务规划决定；命中距离不等于答案质量评分。",
    source: "docs/architecture.md#三类数据的分工",
  },
  calculate: {
    title: "计算工具",
    subtitle: "calc_eval · 表达式",
    description: "实际执行明确的计算表达式，将结果作为工具输出写入 Trace。",
    boundary: "回答中的数字不能代替计算工具的执行记录。",
    source: "docs/tool-execution.md",
  },
  vector: {
    title: "Chroma",
    subtitle: "Memory / RAG 向量",
    description:
      "存储和检索知识向量。文本 embedding 在后端客户端进程计算，API 与导入 worker 都需要模型缓存。",
    boundary: "会话消息保存在 PostgreSQL；当前没有自动长期语义回忆链。",
    source: "docs/architecture.md#embedding-的实际位置",
  },
  ledger: {
    title: "PostgreSQL",
    subtitle: "历史 · Trace · 用量",
    description:
      "业务账本保存会话、任务、Trace、用量与后台导入队列，支持历史查询与增量同步。",
    boundary: "业务数据与向量数据需分别保护；此展示站不读取数据库。",
    source: "docs/architecture.md",
  },
};

export const systemModules: Record<string, ArchitectureModule> = {
  ui: {
    title: "Next.js",
    subtitle: "工作台 · Trace",
    description:
      "完整工作台提供会话、任务、知识库与模型配置界面，通过 REST 查询数据、SSE 合并执行状态与回答。",
    boundary: "浏览器不直接访问数据存储；当前公开站是独立静态应用。",
    source: "frontend/README.md",
  },
  api: {
    title: "FastAPI",
    subtitle: "规划 · 工具 · worker",
    description:
      "后端 API 负责鉴权、任务协调、模型与工具调用。独立后台导入 worker 消费持久化队列并写入 Chroma。",
    boundary:
      "聊天执行由 stream 接管，知识导入由独立 worker 处理，两者不是同一种后台任务。",
    source: "docs/architecture.md",
  },
  model: {
    title: "模型 API",
    subtitle: "规划 / 流式回答",
    description:
      "后端使用用户配置的模型服务进行结构化规划、反馈决策与最终回答，凭据由后端管理。",
    boundary: "公开展示不调用模型，也不接收访客 Key。",
    source: "docs/configuration.md",
  },
  ledger: executionModules.ledger,
  vector: executionModules.vector,
};

// This is a conceptual explanation, not a replay of task events or a claimed DAG.
export const executionGuide = [
  {
    node: "input",
    title: "提交问题",
    edges: ["input-planner"],
    text: "工作台提交任务并接管 SSE，后端准备同会话上下文。",
  },
  {
    node: "planner",
    title: "生成计划",
    edges: ["planner-executor"],
    text: "模型生成结构化计划，后端校验可用工具与依赖。",
  },
  {
    node: "executor",
    title: "调度工具",
    edges: ["executor-retrieve", "executor-calculate"],
    text: "执行器按计划调用工具。下方以知识检索和计算为例，并非每个任务都会调用两者。",
  },
  {
    node: "retrieve",
    title: "检索知识",
    edges: ["executor-retrieve", "retrieve-vector"],
    text: "检索目标知识库，保留来源与版本。向量由后端客户端计算，Chroma 负责存储和检索。",
  },
  {
    node: "calculate",
    title: "执行计算",
    edges: ["executor-calculate"],
    text: "计算工具执行表达式并记录结果，工具输出成为可复核的回答依据。",
  },
  {
    node: "decision",
    title: "反馈循环",
    edges: ["executor-decision", "decision-executor"],
    text: "工具结果进入反馈决策。还需工具时返回执行器；满足结束条件或达到执行边界时进入回答。",
  },
  {
    node: "answer",
    title: "流式回答",
    edges: ["decision-answer", "answer-commit"],
    text: "模型根据实际工具结果生成回答，文本经 SSE 送到工作台。",
  },
  {
    node: "commit",
    title: "保存结果",
    edges: ["commit-ledger"],
    text: "成功状态、Trace、用量与回答一起提交到 PostgreSQL，再发送完成事件。完成后仍可核对执行证据。",
  },
] as const;
