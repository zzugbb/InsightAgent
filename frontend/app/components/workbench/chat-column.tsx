"use client";

import { Alert, Button, Flex, Space, Tag } from "antd";
import type { TextAreaRef } from "antd/es/input/TextArea";
import { ArrowDown } from "lucide-react";
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
  api_key_configured?: boolean;
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
  pendingUserInput: string;
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
  /** 仅窄屏：在标题下展示侧栏入口说明 */
  showNarrowLayoutHint: boolean;
  showStreamRetry: boolean;
  onRetryStream: () => void;
  composerRef: RefObject<TextAreaRef | null>;
  liveRegionText: string;
  runtimeNotice: string | null;
  onOpenModelSettings: () => void;
  onDismissRuntimeNotice: () => void;
  recoveryNotice: {
    type: "info" | "success" | "error";
    text: string;
  } | null;
  onDismissRecoveryNotice: () => void;
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
  pendingUserInput,
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
  showNarrowLayoutHint,
  showStreamRetry,
  onRetryStream,
  composerRef,
  liveRegionText,
  runtimeNotice,
  onOpenModelSettings,
  onDismissRuntimeNotice,
  recoveryNotice,
  onDismissRecoveryNotice,
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
    !sseTokens &&
    !pendingUserInput.trim();
  const sessionLabel = activeSession
    ? getSessionLabel(activeSession, t.workbench)
    : t.chat.newChatTitle;

  const streamFailed = ssePhase === "error" && !isStreaming && Boolean(sseTokens);
  const showLiveAssistant = Boolean(sseTokens) && (isStreaming || streamFailed);
  const showPendingUser = (() => {
    const pending = pendingUserInput.trim();
    if (!pending) {
      return false;
    }
    const last = sessionMessages.at(-1);
    if (!last) {
      return true;
    }
    return !(last.role === "user" && last.content.trim() === pending);
  })();

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
    estimateSize: () => 96,
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
    if (pinnedToBottom) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [
    sessionMessages,
    sseTokens,
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
    !showSessionLoading && (hasHistory || showPendingUser || showLiveAssistant);
  const showScrollFab = hasScrollableFeed && !pinnedToBottom;

  function renderMessageRow(message: SessionMessage, index: number) {
    const prev = index > 0 ? sessionMessages[index - 1] : undefined;
    const showTaskRef =
      Boolean(message.task_id) && message.task_id !== prev?.task_id;
    const roleLabel = getRoleLabel(message.role, t.roles);
    const timeLabel = formatTimestamp(message.created_at, localeTag);

    return (
      <article
        key={message.id}
        className={`message-row ${message.role === "user" ? "user" : "assistant"}`}
        aria-label={`${roleLabel} · ${timeLabel}`}
      >
        <div className="avatar" aria-hidden>
          {message.role === "user"
            ? t.roles.user
            : t.roles.assistantShort}
        </div>
        <div className="message-card">
          <div className="message-card-body">
            {message.role === "user" ? (
              <p className="message-plain">{message.content}</p>
            ) : (
              <MessageBody text={message.content} />
            )}
          </div>
          <footer className="message-card-foot">
            <time dateTime={message.created_at}>{timeLabel}</time>
            {showTaskRef && message.task_id ? (
              <span className="message-task-ref" title={message.task_id}>
                {t.chat.relatedTask(shortenId(message.task_id))}
              </span>
            ) : null}
          </footer>
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
        <Alert
          className="chat-api-alert"
          type="error"
          showIcon
          closable
          onClose={onDismissBanner}
          title={apiBanner}
          role="alert"
        />
      ) : null}
      {!apiBanner && runtimeNotice ? (
        <Alert
          className="chat-api-alert"
          type="warning"
          showIcon
          closable
          onClose={onDismissRuntimeNotice}
          title={runtimeNotice}
          action={
            <Button type="link" size="small" onClick={onOpenModelSettings}>
              {t.chat.goConfigureModel}
            </Button>
          }
        />
      ) : null}
      {!apiBanner && !runtimeNotice && recoveryNotice ? (
        <Alert
          className="chat-api-alert"
          type={recoveryNotice.type}
          showIcon
          closable
          onClose={onDismissRecoveryNotice}
          title={recoveryNotice.text}
        />
      ) : null}

      <header className="chat-header">
        <div className="chat-header-lead">
          <h2 id="chat-main-title" className="chat-main-heading">
            <span className="chat-title-row">
              <span className="chat-title-text">
                {sessionLabel}
              </span>
              {activeSession ? (
                <>
                  <span className="chat-title-divider" aria-hidden />
                  <span className="chat-title-time-wrap">
                    <span className="chat-title-time">
                      {t.chat.updatedAt(
                        formatTimestamp(activeSession.updated_at, localeTag),
                      )}
                    </span>
                  </span>
                </>
              ) : null}
            </span>
          </h2>
        </div>
        <Flex wrap="wrap" gap="small" align="center" justify="flex-end" className="chat-header-actions">
          <Space wrap size="small">
            {showSessionDrawerTrigger ? (
              <Button
                ref={sessionDrawerTriggerRef}
                type="default"
                className="mobile-inspector-trigger"
                onClick={onOpenSessionDrawer}
              >
                {t.chat.sessionList}
              </Button>
            ) : null}
            {showInspectorTrigger ? (
              <Button
                ref={inspectorDrawerTriggerRef}
                type="default"
                className="mobile-inspector-trigger"
                onClick={onOpenInspector}
              >
                {t.chat.traceAndContext}
              </Button>
            ) : null}
          </Space>
          <div className="chat-runtime-badges" aria-label="runtime">
            <Tag variant="filled" className="header-badge-tag header-badge-tag--mode">
              <span className="header-badge-label">{t.chat.modeLabel}</span>
              <span className="header-badge-value">
                {settingsSummary?.mode ?? "—"}
              </span>
            </Tag>
            <Tag variant="filled" className="header-badge-tag header-badge-tag--stack">
              <span className="header-badge-value header-badge-value--mono">
                {settingsSummary?.provider ?? "—"}
              </span>
              <span className="header-badge-sep" aria-hidden>
                /
              </span>
              <span className="header-badge-value header-badge-value--mono header-badge-value--model">
                {settingsSummary?.model ?? "—"}
              </span>
            </Tag>
          </div>
        </Flex>
      </header>

      {showNarrowLayoutHint ? (
        <p className="chat-hint-row">{t.workbench.hintRowNarrow}</p>
      ) : null}

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

        {!showSessionLoading && (hasHistory || showPendingUser || showLiveAssistant) ? (
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
                      {renderMessageRow(row.message, vi.index)}
                    </div>
                  );
                })}
              </div>
            ) : (
              sessionMessages.map((m, i) => renderMessageRow(m, i))
            )}

            {showPendingUser ? (
              <article className="message-row user pending">
                <div className="avatar" aria-hidden>
                  {t.roles.user}
                </div>
                <div className="message-card">
                  <div className="message-card-body">
                    <p className="message-plain">{pendingUserInput.trim()}</p>
                  </div>
                  <footer className="message-card-foot message-card-foot--live">
                    <span className="message-live-status">
                      {t.chat.streamOutputting}
                    </span>
                  </footer>
                </div>
              </article>
            ) : null}

            {showLiveAssistant ? (
              <article
                className={`message-row assistant live${streamFailed ? " message-row--failed" : ""}`}
              >
                <div className="avatar" aria-hidden>
                  {t.roles.assistantShort}
                </div>
                <div className="message-card message-card--streaming">
                  {streamFailed ? (
                    <p className="stream-failed-badge" role="status">
                      {t.workbench.streamFailedBadge}
                    </p>
                  ) : null}
                  <div className="message-card-body">
                    <MessageBody text={sseTokens} />
                  </div>
                  <footer className="message-card-foot message-card-foot--live">
                    <span className="message-live-status">
                      {isStreaming
                        ? t.chat.streamOutputting
                        : streamFailed
                          ? t.chat.streamInterrupted
                          : t.chat.streamLatest}
                    </span>
                  </footer>
                </div>
              </article>
            ) : null}
          </div>
        ) : null}

        {showScrollFab ? (
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={<ArrowDown size={20} aria-hidden />}
            className="scroll-bottom-fab"
            onClick={scrollToBottom}
            aria-label={t.chat.scrollToBottomAria}
            title={t.chat.scrollToBottom}
          />
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

        {!showSessionLoading && (hasHistory || showPendingUser || showLiveAssistant) ? (
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
        sendDisabled={sendDisabled}
        sending={isStreaming}
        hint={composerHint}
        hintVariant={composerHintVariant}
        showRetry={showStreamRetry}
        onRetry={onRetryStream}
      />
    </section>
  );
}
