import { Database, Layers3, Radio, Terminal } from "lucide-react";
import { systemModules } from "../lib/architecture";

export function ArchitectureOverview({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="architecture-overview">
      <div
        className="architecture-diagram"
        aria-label="Next.js 通过 REST 和 SSE 访问 FastAPI；后端调用模型、PostgreSQL 和 Chroma"
      >
        <button
          className="arch-node"
          aria-pressed={selected === "ui"}
          onClick={() => onSelect("ui")}
        >
          <Layers3 />
          <strong>Next.js</strong>
          <span>工作台 · Trace</span>
        </button>
        <div className="arch-connector">REST / SSE</div>
        <button
          className="arch-node"
          aria-pressed={selected === "api"}
          onClick={() => onSelect("api")}
        >
          <Terminal />
          <strong>FastAPI</strong>
          <span>规划 · 工具 · worker</span>
        </button>
        <div className="arch-branches">
          {(["model", "ledger", "vector"] as const).map((id) => {
            const Icon = id === "model" ? Radio : Database;
            return (
              <button
                key={id}
                aria-pressed={selected === id}
                onClick={() => onSelect(id)}
              >
                <Icon />
                <strong>{systemModules[id].title}</strong>
                <span>{systemModules[id].subtitle}</span>
              </button>
            );
          })}
        </div>
      </div>
      <p className="architecture-note">
        保留完整应用的系统总览。点击模块，查看职责与运行边界。
      </p>
    </div>
  );
}
