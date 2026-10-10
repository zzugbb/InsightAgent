"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { ArrowUpRight, Pause, Play, RotateCcw } from "lucide-react";
import {
  executionGuide,
  executionModules,
  systemModules,
} from "../lib/architecture";
import { repository } from "../lib/labels";
import { ArchitectureOverview } from "./architecture-overview";
import "./architecture.css";

const ArchitectureGraph = dynamic(() => import("./architecture-graph"), {
  ssr: false,
  loading: () => (
    <div className="architecture-loading">
      正在加载执行图…下方可选择步骤查看讲解。
    </div>
  ),
});

export function ArchitectureExplorer() {
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState("input");
  const [playing, setPlaying] = useState(false);
  const [graphLoaded, setGraphLoaded] = useState(false);
  const graphReady = useRef(false);
  const inView = useRef(false);
  const autoplayConsumed = useRef(false);
  const tryAutoplay = useCallback(() => {
    if (!inView.current || !graphReady.current || autoplayConsumed.current)
      return;
    autoplayConsumed.current = true;
    if (
      !document.hidden &&
      !matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setPlaying(true);
    }
  }, []);
  const onReady = useCallback(() => {
    graphReady.current = true;
    tryAutoplay();
  }, [tryAutoplay]);
  const canvas = useRef<HTMLDivElement>(null);
  const guide = executionGuide[step];
  const info = executionModules[selected];
  const finished = step === executionGuide.length - 1;

  useEffect(() => {
    if (!canvas.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setGraphLoaded(true);
          observer.disconnect();
        }
      },
      { rootMargin: "180px" },
    );
    observer.observe(canvas.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!canvas.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        const visible = entry.isIntersecting && entry.intersectionRatio >= 0.25;
        inView.current = visible;
        if (visible) tryAutoplay();
        else setPlaying(false);
      },
      { threshold: [0, 0.25] },
    );
    observer.observe(canvas.current);
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const stop = () => {
      if (document.hidden || motion.matches) {
        autoplayConsumed.current = true;
        setPlaying(false);
      }
    };
    document.addEventListener("visibilitychange", stop);
    motion.addEventListener("change", stop);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", stop);
      motion.removeEventListener("change", stop);
    };
  }, [tryAutoplay]);

  useEffect(() => {
    if (!playing || finished) return;
    const timer = setTimeout(() => {
      const next = step + 1;
      setStep(next);
      setSelected(executionGuide[next].node);
      if (next === executionGuide.length - 1) setPlaying(false);
    }, 1800);
    return () => clearTimeout(timer);
  }, [step, playing, finished]);

  const select = useCallback((id: string) => {
    autoplayConsumed.current = true;
    setPlaying(false);
    setSelected(id);
    const index = executionGuide.findIndex((item) => item.node === id);
    if (index >= 0) setStep(index);
  }, []);
  const reset = () => {
    autoplayConsumed.current = true;
    setStep(0);
    setSelected("input");
    setPlaying(false);
  };
  return (
    <div className="architecture-explorer">
      <div className="architecture-toolbar">
        <span className="architecture-caption">主流程 / 工具 / 反馈</span>
        <span className="architecture-caption architecture-autoplay-hint">
          进入视野播放一次 · 随时暂停
        </span>
        <span className="architecture-caption architecture-reduced-hint">
          已减少动态效果 · 手动播放
        </span>
      </div>
      <div ref={canvas} className="architecture-canvas">
        {graphLoaded ? (
          <ArchitectureGraph
            selected={selected}
            activeEdges={selected === guide.node ? [...guide.edges] : []}
            playing={playing}
            onSelect={select}
            onReady={onReady}
          />
        ) : (
          <div className="architecture-loading">
            任务输入 → 模型规划 → 工具执行 → 反馈决策 → 流式回答 → 保存结果
          </div>
        )}
      </div>
      <div className="architecture-playback">
        <div className="play-controls">
          <button
            className="button primary compact"
            aria-label={
              playing
                ? "暂停架构讲解"
                : finished
                  ? "重新播放架构讲解"
                  : "播放架构讲解"
            }
            onClick={() => {
              autoplayConsumed.current = true;
              if (finished) {
                setStep(0);
                setSelected("input");
              } else setSelected(guide.node);
              setPlaying(!playing);
            }}
          >
            {playing ? <Pause size={16} /> : <Play size={16} />}
            {playing ? "暂停" : finished ? "重新播放" : "播放讲解"}
          </button>
          <button
            className="icon-button"
            aria-label="复位架构讲解"
            onClick={reset}
          >
            <RotateCcw size={17} />
          </button>
          <span
            className="architecture-progress"
            role="progressbar"
            aria-label="架构讲解进度"
            aria-valuemin={1}
            aria-valuemax={executionGuide.length}
            aria-valuenow={step + 1}
          >
            {String(step + 1).padStart(2, "0")} /{" "}
            {String(executionGuide.length).padStart(2, "0")}
          </span>
        </div>
        <p className="architecture-narration" aria-live="polite">
          {guide.text}
        </p>
      </div>
      <div className="architecture-steps" aria-label="选择讲解步骤">
        {executionGuide.map((item, index) => (
          <button
            key={item.title}
            aria-pressed={step === index}
            onClick={() => {
              setStep(index);
              select(item.node);
            }}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            {item.title}
          </button>
        ))}
      </div>
      <ModuleInspector info={info} label="执行节点说明" />
      <p className="architecture-note">
        架构讲解为示意动画。当前展示站独立静态运行，不连接后端、数据库或模型
        API；真实执行证据见案例回放。
      </p>
    </div>
  );
}

function ModuleInspector({
  info,
  label,
}: {
  info: (typeof executionModules)[string];
  label: string;
}) {
  return (
    <div className="architecture-inspector" role="region" aria-label={label}>
      <div>
        <span className="detail-label">模块职责</span>
        <h3>{info.title}</h3>
        <small>{info.subtitle}</small>
      </div>
      <div>
        <p>{info.description}</p>
        <p className="architecture-boundary">{info.boundary}</p>
      </div>
      <a
        className="text-link"
        href={`${repository}/blob/main/${info.source}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        源码依据
        <ArrowUpRight size={15} />
      </a>
    </div>
  );
}

export function SystemArchitectureExplorer() {
  const [selected, setSelected] = useState("ui");
  return (
    <div className="architecture-explorer system-explorer">
      <ArchitectureOverview selected={selected} onSelect={setSelected} />
      <ModuleInspector info={systemModules[selected]} label="系统模块说明" />
    </div>
  );
}
