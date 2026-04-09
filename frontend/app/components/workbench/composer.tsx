"use client";

import { Button, Input, Space } from "antd";
import type { TextAreaRef } from "antd/es/input/TextArea";
import {
  FormEvent,
  forwardRef,
  KeyboardEvent,
  type Ref,
} from "react";

import { useMessages } from "../../../lib/preferences-context";

import { useMediaQuery } from "./use-media-query";

const COMPACT_COMPOSER_QUERY = "(max-width: 720px)";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  /** 不可点击发送（空内容或流式中） */
  sendDisabled: boolean;
  /** 流式生成中，用于按钮 loading */
  sending: boolean;
  hint: string;
  hintVariant?: "default" | "error";
  showRetry?: boolean;
  onRetry?: () => void;
};

export const Composer = forwardRef(function Composer(
  {
    value,
    onChange,
    onSend,
    sendDisabled,
    sending,
    hint,
    hintVariant = "default",
    showRetry,
    onRetry,
  }: ComposerProps,
  ref: Ref<TextAreaRef | null>,
) {
  const t = useMessages();
  const compactComposer = useMediaQuery(COMPACT_COMPOSER_QUERY);
  /** 与 ChatGPT 类似：空状态约一行，随内容增高（勿用 CSS 固定 min-height 压死高度） */
  const minRows = 1;
  const maxRows = compactComposer ? 12 : 18;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sendDisabled) {
      onSend();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!sendDisabled) {
        onSend();
      }
    }
  }

  return (
    <form className="composer-shell" onSubmit={handleSubmit}>
      <Input.TextArea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t.composer.placeholder}
        title={t.workbench.cmdKHint}
        rows={minRows}
        autoSize={{ minRows, maxRows }}
        aria-label={t.composer.inputAria}
        className="composer-textarea"
      />
      <div className="composer-footer">
        <div className="composer-footer-main">
          <p className={`composer-hint composer-hint--${hintVariant}`}>
            {hint}
          </p>
          {showRetry && onRetry ? (
            <Button
              type="default"
              className="composer-retry"
              onClick={onRetry}
            >
              {t.composer.retry}
            </Button>
          ) : null}
        </div>
        <div className="composer-actions">
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              disabled={sendDisabled}
              loading={sending}
            >
              {sending ? t.composer.sending : t.composer.send}
            </Button>
          </Space>
        </div>
      </div>
    </form>
  );
});
