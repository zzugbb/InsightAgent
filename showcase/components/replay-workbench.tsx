"use client";
import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Markdown from "react-markdown";
import {
  Play,
  Pause,
  RotateCcw,
  List,
  Workflow,
  ArrowLeft,
  FileText,
  CircleCheck,
  CircleAlert,
  GitBranch,
} from "lucide-react";
import Link from "next/link";
import records from "../data/cases.json";
import type { Run } from "../lib/types";
import { isError, stepKind, stepTitle } from "../lib/labels";
import { StepDetail } from "./step-detail";
const TraceGraph = dynamic(() => import("./trace-graph"), {
  ssr: false,
  loading: () => <p className="empty-trace">正在加载流程图…</p>,
});
const runs = records as unknown as Run[];
export function ReplayWorkbench() {
  const [caseId, setCaseId] = useState("rag");
  const [branch, setBranch] = useState("failure");
  const [count, setCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState("timeline");
  const run = runs.find(
    (item) => item.id === (caseId === "rag" ? "rag" : branch),
  )!;
  const visible = run.steps.slice(0, count);
  const done = count === run.steps.length;
  const activeStep = visible.find((step) => step.id === selected);
  const reset = () => {
    setCount(0);
    setPlaying(false);
    setSelected(null);
  };
  const select = useCallback((id: string) => setSelected(id), []);
  useEffect(() => {
    if (!playing || count >= run.steps.length) return;
    const timer = setTimeout(() => {
      setCount(count + 1);
      setSelected(run.steps[count].id);
      if (count + 1 === run.steps.length) setPlaying(false);
    }, 1100);
    return () => clearTimeout(timer);
  }, [playing, count, run]);
  const playbackStatus = done
    ? "回放结束"
    : playing
      ? "正在回放"
      : count > 0
        ? "已暂停"
        : "尚未播放";
  return (
    <>
      <Link className="back-link" href="/">
        <ArrowLeft size={15} />
        项目首页
      </Link>
      <div className="demo-heading">
        <div>
          <h1>展开一次执行。</h1>
          <p>沿着 Trace 查看任务如何规划、调用工具并形成回答。</p>
        </div>
        <span className="replay-label">
          <span className="status-dot" />
          预录案例回放
        </span>
      </div>
      <div className="case-tabs" aria-label="选择演示案例">
        <button
          aria-pressed={caseId === "rag"}
          className={caseId === "rag" ? "active" : ""}
          onClick={() => {
            setCaseId("rag");
            reset();
          }}
        >
          <span>01</span>知识检索与计算
        </button>
        <button
          aria-pressed={caseId === "recovery"}
          className={caseId === "recovery" ? "active" : ""}
          onClick={() => {
            setCaseId("recovery");
            setBranch("failure");
            reset();
          }}
        >
          <span>02</span>失败与分支恢复
        </button>
      </div>
      {caseId === "recovery" && (
        <div className="branch-bar">
          <GitBranch size={18} />
          <div className="branch-switch" aria-label="查看原任务或分支">
            <button
              aria-pressed={branch === "failure"}
              onClick={() => {
                setBranch("failure");
                reset();
              }}
            >
              原任务 · 受控失败
            </button>
            <span>→</span>
            <button
              aria-pressed={branch === "recovery"}
              onClick={() => {
                setBranch("recovery");
                reset();
              }}
            >
              独立分支 · 真实模型
            </button>
          </div>
          <p>恢复成功保留原失败记录，不回滚原任务。</p>
        </div>
      )}
      <div className="prompt-panel">
        <span className="detail-label">任务输入</span>
        <p>{run.prompt}</p>
      </div>
      <section className="replay-surface" aria-label="执行记录回放">
        <div className="replay-toolbar">
          <div className="play-controls">
            <button
              className="button primary compact"
              aria-label={playing ? "暂停回放" : done ? "重新播放" : "播放回放"}
              onClick={() => {
                if (done) {
                  setCount(0);
                  setSelected(null);
                }
                setPlaying(!playing);
              }}
            >
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? "暂停" : done ? "重新播放" : "播放"}
            </button>
            <button
              className="icon-button"
              aria-label="复位回放"
              onClick={reset}
            >
              <RotateCcw size={17} />
            </button>
            <span className="playback-status" aria-live="polite">
              {playbackStatus}
              <span>
                {count} / {run.steps.length}
              </span>
            </span>
          </div>
          <div className="view-switch" aria-label="Trace 视图">
            <button
              aria-pressed={view === "timeline"}
              onClick={() => setView("timeline")}
            >
              <List size={16} />
              时间线
            </button>
            <button
              aria-pressed={view === "flow"}
              onClick={() => setView("flow")}
            >
              <Workflow size={16} />
              流程图
            </button>
          </div>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label="回放进度"
          aria-valuenow={count}
          aria-valuemin={0}
          aria-valuemax={run.steps.length}
        >
          <div style={{ width: `${(count / run.steps.length) * 100}%` }} />
        </div>
        <div className="replay-grid">
          <div className="trace-pane">
            <div className="pane-title">
              <h2>Execution Trace</h2>
              <span>
                实际记录 /{" "}
                {run.source === "real_model" ? run.model : "受控 fixture"}
              </span>
            </div>
            {visible.length === 0 ? (
              <div className="empty-trace">
                <Workflow size={36} strokeWidth={1.3} />
                <h3>从第一个步骤开始</h3>
                <p>
                  播放后逐步呈现已保存的执行记录。
                  <br />
                  随时暂停，点击节点查看详情。
                </p>
              </div>
            ) : view === "flow" ? (
              <TraceGraph
                steps={visible}
                selected={selected}
                onSelect={select}
              />
            ) : (
              <ol className="timeline">
                {visible.map((step, index) => (
                  <li key={step.id}>
                    <button
                      className={`timeline-step ${selected === step.id ? "selected" : ""} ${isError(step) ? "error" : ""}`}
                      aria-pressed={selected === step.id}
                      onClick={() => select(step.id)}
                    >
                      <span className="step-index">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="step-summary">
                        <span className="step-topline">
                          <strong>{stepTitle(step)}</strong>
                          <span>{stepKind(step)}</span>
                        </span>
                        <span className="step-preview">
                          {step.meta?.tool?.result_summary || step.content}
                        </span>
                      </span>
                      {isError(step) ? (
                        <CircleAlert size={17} />
                      ) : (
                        <CircleCheck size={17} />
                      )}
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </div>
          <aside className="detail-pane" aria-label="节点详情">
            <div className="pane-title">
              <h2>节点详情</h2>
              <FileText size={16} />
            </div>
            <StepDetail step={activeStep} />
          </aside>
        </div>
        {done && (
          <div
            className={`answer-panel ${run.status === "failed" ? "error" : ""}`}
          >
            <div className="answer-heading">
              {run.status === "failed" ? (
                <CircleAlert size={19} />
              ) : (
                <CircleCheck size={19} />
              )}
              <h2>
                {run.status === "failed"
                  ? "原任务失败，执行证据已保留"
                  : "最终回答"}
              </h2>
              <span>{run.status}</span>
            </div>
            {run.answer ? (
              <div className="markdown">
                <Markdown>{run.answer}</Markdown>
              </div>
            ) : (
              <p>
                受控 fixture
                在后续决策阶段返回错误，本任务没有生成最终回答。切换独立分支，查看明确输入后的真实执行结果。
              </p>
            )}
          </div>
        )}
      </section>
      <section className="provenance">
        <div>
          <h2>这段记录来自哪里？</h2>
          <p>
            {run.source === "real_model"
              ? `真实 glm-5.3 回答，工具由项目实际执行。${run.steps[0].meta?.planning_provider_used ? "首轮使用真实模型规划。" : "首轮模型规划未成功，采用既有规则回退；不算完整真实规划成功。"}资料为专用合成内容。`
              : "使用仓库已有 ConditionalProvider(stop=error) 受控 fixture；第一次实际计算成功后，后续决策注入 429 错误。不是供应商真实故障。"}
          </p>
          <p>
            当前只回放静态记录，不发起模型调用。播放节奏为阅读而缩短，不代表原始耗时。
          </p>
        </div>
        <dl>
          <div>
            <dt>采集日期</dt>
            <dd>{run.preparedAt.slice(0, 10)}</dd>
          </div>
          <div>
            <dt>原始执行耗时</dt>
            <dd>{run.elapsedSeconds.toFixed(2)} 秒</dd>
          </div>
          <div>
            <dt>已记录总 tokens</dt>
            <dd>
              {run.usage?.overall_total_tokens?.toLocaleString() ??
                (run.source === "controlled_fixture"
                  ? "替身用量不计入"
                  : "未知")}
            </dd>
          </div>
          <div>
            <dt>源码基线</dt>
            <dd>
              <code>{run.sourceCommit.slice(0, 7)}</code>
            </dd>
          </div>
        </dl>
      </section>
      <p className="demo-footnote">
        执行记录支持复核，不保证模型回答绝不误述。已记录用量不等于供应商账单；恢复分支不覆盖原任务结论。
      </p>
    </>
  );
}
