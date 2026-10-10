import Markdown from "react-markdown";
import { CircleCheck, CircleAlert, FileText } from "lucide-react";
import type { TraceStepPayload } from "../lib/types";
import { isError, stepKind, stepTitle } from "../lib/labels";
const format = (value: unknown) =>
  typeof value === "string" ? value : JSON.stringify(value, null, 2);
export function StepDetail({ step }: { step: TraceStepPayload | undefined }) {
  if (!step)
    return (
      <div className="detail-empty">
        <FileText size={28} />
        <h3>执行记录已准备就绪</h3>
        <p>回放逐步呈现记录；选择已显示的节点，查看实际输入、输出与来源。</p>
      </div>
    );
  const tool = step.meta?.tool;
  const chunks = step.meta?.rag?.chunk_metadata ?? [];
  return (
    <div className="step-detail" key={step.id}>
      <div className="detail-label">
        {stepKind(step)} / 记录序号 {step.seq ?? "—"}
      </div>
      <h3>{stepTitle(step)}</h3>
      {tool && (
        <div className={`tool-state ${isError(step) ? "error" : "success"}`}>
          {isError(step) ? (
            <CircleAlert size={16} />
          ) : (
            <CircleCheck size={16} />
          )}
          {tool.status === "done"
            ? "已执行"
            : tool.status === "error"
              ? "执行失败"
              : tool.status}
          <span>{tool.name}</span>
        </div>
      )}
      <div className="markdown step-content">
        <Markdown>{step.content}</Markdown>
      </div>
      {tool?.input !== undefined && (
        <section>
          <h4>工具输入</h4>
          <pre>{format(tool.input)}</pre>
        </section>
      )}
      {tool?.output_preview !== undefined && (
        <section>
          <h4>公开结果</h4>
          <pre>{format(tool.output_preview)}</pre>
        </section>
      )}
      {tool?.error && (
        <section className="error">
          <h4>错误</h4>
          <p>{tool.error}</p>
        </section>
      )}
      {step.meta?.error_event && (
        <section className="error">
          <h4>错误记录</h4>
          <pre>{format(step.meta.error_event)}</pre>
        </section>
      )}
      {chunks.length > 0 && (
        <section>
          <h4>引用来源</h4>
          {chunks.map((chunk, index) => (
            <div className="citation" key={index}>
              <FileText size={15} />
              <div>
                <strong>{chunk.source || "来源未记录"}</strong>
                <span>{chunk.document_version || "版本未记录"}</span>
              </div>
            </div>
          ))}
        </section>
      )}
      {step.meta?.rag?.chunks?.map((chunk, index) => (
        <section key={index}>
          <h4>知识片段 {index + 1}</h4>
          <p>{chunk}</p>
        </section>
      ))}
      <dl className="step-metrics">
        <div>
          <dt>阶段耗时</dt>
          <dd>
            {step.meta?.latency == null ? "未记录" : `${step.meta.latency} ms`}
          </dd>
        </div>
        <div>
          <dt>阶段 tokens</dt>
          <dd>
            {step.meta?.tokens == null
              ? "未记录"
              : step.meta.tokens.toLocaleString()}
          </dd>
        </div>
      </dl>
    </div>
  );
}
