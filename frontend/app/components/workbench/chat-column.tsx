"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import {
  useMessages,
  usePreferences,
} from "../../../lib/preferences-context";

import type { SessionMessage, SessionSummary } from "./types";
import {
  formatTimestamp,
  getRoleLabel,
  getSessionLabel,
  shortenId,
} from "./utils";
import { Composer } from "./composer";
import { MessageBody } from "./message-body";

type SettingsSummaryLite = {
  mode: string;
  provider: string;
  model: string;
} | null;

const MSG_VIRTUAL_THRESHOLD = 24;

type ChatColumnProps = {
  activeSession: SessionSummary | undefined;
  activeSessionId: string | null;
  settingsSummary: SettingsSummaryLite;
  isStreaming: boolean;
  apiBanner: string | null;
  onDismissBanner: () => void;
  sessionMessages: SessionMessage[];
  messagesLoading: boolean;
  messagesMessage: string;
  sseTokens: string;
  ssePhase: string | null;
  prompt: string;
  onPromptChange: (value: string) => void;
  onSend: () => void | Promise<void>;
  sendDisabled: boolean;
  composerHint: string;
  composerHintVariant: "default" | "error";
  showSessionDrawerTrigger: boolean;
  onOpenSessionDrawer: () => void;
  sessionDrawerTriggerRef?: RefObject<HTMLButtonElement | null>;
  showInspectorTrigger: boolean;
  onOpenInspector: () => void;
  inspectorDrawerTriggerRef?: RefObject<HTMLButtonElement | null>;
  showStreamRetry: boolean;
  onRetryStream: () => void;
  composerRef: RefObject<HTMLTextAreaElement | null>;
  liveRegionText: string;
};

const SCROLL_BOTTOM_THRESHOLD = 96;

export function ChatColumn({
  activeSession,
  activeSessionId,
  settingsSummary,
  isStreaming,
  apiBanner,
  onDismissBanner,
  sessionMessages,
  messagesLoading,
  messagesMessage,
  sseTokens,
  ssePhase,
  prompt,
  onPromptChange,
  onSend,
  sendDisabled,
  composerHint,
  composerHintVariant,
  showSessionDrawerTrigger,
  onOpenSessionDrawer,
  sessionDrawerTriggerRef,
  showInspectorTrigger,
  onOpenInspector,
  inspectorDrawerTriggerRef,
  showStreamRetry,
  onRetryStream,
  composerRef,
  liveRegionText,
}: ChatColumnProps) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const hasHistory = sessionMessages.length > 0;
  const showOnboarding =
    !activeSessionId && !messagesLoading && !hasHistory && !sseTokens;
  const showSessionLoading = Boolean(activeSessionId && messagesLoading);
  const showSessionEmpty =
    Boolean(activeSessionId) &&
    !messagesLoading &&
    !hasHistory &&
    !sseTokens;

  const streamFailed = ssePhase === "error" && !isStreaming && Boolean(sseTokens);

  const stageRef = useRef<HTMLElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const [pinnedToBottom, setPinnedToBottom] = useState(true);

  const flatRows = useMemo(() => {
    const rows: { kind: "msg"; message: SessionMessage }[] = sessionMessages.map(
      (m) => ({ kind: "msg" as const, message: m }),
    );
    return rows;
  }, [sessionMessages]);

  const useMsgVirtual =
    flatRows.length > MSG_VIRTUAL_THRESHOLD && !showSessionLoading;

  const msgVirtualizer = useVirtualizer({
    count: useMsgVirtual ? flatRows.length : 0,
    getScrollElement: () => stageRef.current,
    estimateSize: () => 120,
    overscan: 4,
  });

  const updatePinnedFromScroll = useCallback(() => {
    const el = stageRef.current;
    if (!el) return;
    const gap = el.scrollHeight - el.scrollTop - el.clientHeight;
    setPinnedToBottom(gap < SCROLL_BOTTOM_THRESHOLD);
  }, []);

  useEffect(() => {
    const el = stageRef.current;
    if (!el || messagesLoading) return;
    if (pinnedToBottom || isStreaming) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [
    sessionMessages,
    sseTokens,
    isStreaming,
    messagesLoading,
    pinnedToBottom,
    useMsgVirtual,
  ]);

  const scrollToBottom = useCallback(() => {
    const el = stageRef.current;
    if (!el) return;
    setPinnedToBottom(true);
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }, []);

  const hasScrollableFeed =
    !showSessionLoading && (hasHistory || Boolean(sseTokens));
  const showScrollFab = hasScrollableFeed && !pinnedToBottom;

  function renderMessageRow(message: SessionMessage) {
    return (
      <article
        key={message.id}
        className={`message-row ${message.role === "user" ? "user" : "assistant"}`}
      >
        <div className="avatar" aria-hidden>
          {message.role === "user"
            ? t.roles.user
            : t.roles.assistantShort}
        </div>
        <div className="message-card">
          <div className="message-meta">
            <strong>{getRoleLabel(message.role, t.roles)}</strong>
            <span>{formatTimestamp(message.created_at, localeTag)}</span>
          </div>
          {message.role === "user" ? (
            <p className="message-plain">{message.content}</p>
          ) : (
            <MessageBody text={message.content} />
          )}
          {message.task_id ? (
            <div className="message-tag">
              {t.chat.relatedTask(shortenId(message.task_id))}
            </div>
          ) : null}
        </div>
      </article>
    );
  }

  return (
    <section className="chat-shell">
      <div
        className="live-region"
        aria-live="polite"
        aria-atomic="true"
      >
        {liveRegionText}
      </div>

      {apiBanner ? (
        <div className="api-banner" role="alert">
          <p>{apiBanner}</p>
          <button
            type="button"
            className="api-banner-dismiss"
            onClick={onDismissBanner}
          >
            {t.chat.closeBanner}
          </button>
        </div>
      ) : null}

      <header className="chat-header">
        <div>
          <p className="chat-kicker">{t.chat.kicker}</p>
          <h2 id="chat-main-title">
            {activeSession
              ? getSessionLabel(activeSession, t.workbench)
              : t.chat.newChatTitle}
          </h2>
          <p className="chat-subtitle">
            {activeSession
              ? t.chat.updatedAt(
                  formatTimestamp(activeSession.updated_at, localeTag),
                )
              : t.chat.autoCreateHint}
          </p>
        </div>
        <div className="chat-header-actions">
          {showSessionDrawerTrigger ? (
            <button
              ref={sessionDrawerTriggerRef}
              type="button"
              className="secondary-button mobile-inspector-trigger"
              onClick={onOpenSessionDrawer}
            >
              {t.chat.sessionList}
            </button>
          ) : null}
          {showInspectorTrigger ? (
            <button
              ref={inspectorDrawerTriggerRef}
              type="button"
              className="secondary-button mobile-inspector-trigger"
              onClick={onOpenInspector}
            >
              {t.chat.traceAndContext}
            </button>
          ) : null}
          <div className="header-badges">
            <span className="header-badge">
              {t.chat.modeLabel} {settingsSummary?.mode ?? "—"}
            </span>
            <span className="header-badge">
              {settingsSummary?.provider ?? "—"} /{" "}
              {settingsSummary?.model ?? "—"}
            </span>
            <span className={`header-badge ${isStreaming ? "accent" : ""}`}>
              {isStreaming ? t.chat.generating : t.chat.ready}
            </span>
          </div>
        </div>
      </header>

      <p className="chat-hint-row">
        {t.workbench.cmdKHint}。{t.workbench.hintRowNarrow}
      </p>

      <section
        ref={stageRef}
        className="message-stage"
        onScroll={updatePinnedFromScroll}
        aria-labelledby="chat-main-title"
      >
        {showSessionLoading ? (
          <div className="message-skeleton-wrap message-skeleton-wrap--solo">
            <div className="skeleton message-skeleton-row" />
            <div className="skeleton message-skeleton-row" />
          </div>
        ) : null}

        {!showSessionLoading && (hasHistory || sseTokens) ? (
          <div ref={feedRef} className="message-feed">
            {useMsgVirtual ? (
              <div
                style={{
                  height: msgVirtualizer.getTotalSize(),
                  position: "relative",
                  width: "100%",
                }}
              >
                {msgVirtualizer.getVirtualItems().map((vi) => {
                  const row = flatRows[vi.index];
                  return (
                    <div
                      key={row.message.id}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        transform: `translateY(${vi.start}px)`,
                      }}
                    >
                      {renderMessageRow(row.message)}
                    </div>
                  );
                })}
              </div>
            ) : (
              sessionMessages.map((m) => renderMessageRow(m))
            )}

            {sseTokens ? (
              <article
                className={`message-row assistant live${streamFailed ? " message-row--failed" : ""}`}
              >
                <div className="avatar" aria-hidden>
                  {t.roles.assistantShort}
                </div>
                <div className="message-card">
                  <div className="message-meta">
                    <strong>{t.roles.assistantName}</strong>
                    <span>
                      {isStreaming
                        ? t.chat.streamOutputting
                        : streamFailed
                          ? t.chat.streamInterrupted
                          : t.chat.streamLatest}
                    </span>
                  </div>
                  {streamFailed ? (
                    <p className="stream-failed-badge" role="status">
                      {t.workbench.streamFailedBadge}
                    </p>
                  ) : null}
                  <MessageBody text={sseTokens} />
                </div>
              </article>
            ) : null}
          </div>
        ) : null}

        {showScrollFab ? (
          <button
            type="button"
            className="scroll-bottom-fab"
            onClick={scrollToBottom}
            aria-label={t.chat.scrollToBottomAria}
          >
            {t.chat.scrollToBottom}
          </button>
        ) : null}

        {showSessionEmpty ? (
          <div className="empty-hero empty-hero--compact">
            <h3>{t.chat.sessionEmptyTitle}</h3>
            <p>{t.chat.sessionEmptyLead}</p>
          </div>
        ) : null}

        {showOnboarding ? (
          <div className="empty-hero empty-hero--single">
            <h3>{t.chat.onboardingTitle}</h3>
            <p>{t.chat.onboardingLead}</p>
          </div>
        ) : null}

        {!showSessionLoading && (hasHistory || sseTokens) ? (
          <p className="message-stage-footnote">{messagesMessage}</p>
        ) : null}
      </section>

      <Composer
        ref={composerRef}
        value={prompt}
        onChange={onPromptChange}
        onSend={() => {
          void onSend();
        }}
        disabled={sendDisabled}
        hint={composerHint}
        hintVariant={composerHintVariant}
        showRetry={showStreamRetry}
        onRetry={onRetryStream}
      />
    </section>
  );
}
