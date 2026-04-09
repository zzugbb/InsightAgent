"use client";

import {
  FormEvent,
  forwardRef,
  KeyboardEvent,
  type Ref,
} from "react";

import { useMessages } from "../../../lib/preferences-context";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
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
    disabled,
    hint,
    hintVariant = "default",
    showRetry,
    onRetry,
  }: ComposerProps,
  ref: Ref<HTMLTextAreaElement>,
) {
  const t = useMessages();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!disabled) {
      onSend();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled) {
        onSend();
      }
    }
  }

  return (
    <form className="composer-shell" onSubmit={handleSubmit}>
      <textarea
        ref={ref}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t.composer.placeholder}
        rows={4}
        aria-label={t.composer.inputAria}
      />
      <div className="composer-footer">
        <div className="composer-footer-main">
          <p className={`composer-hint composer-hint--${hintVariant}`}>
            {hint}
          </p>
          {showRetry && onRetry ? (
            <button
              type="button"
              className="secondary-button composer-retry"
              onClick={onRetry}
            >
              {t.composer.retry}
            </button>
          ) : null}
        </div>
        <div className="composer-actions">
          <button className="primary-button" disabled={disabled} type="submit">
            {disabled ? t.composer.sending : t.composer.send}
          </button>
        </div>
      </div>
    </form>
  );
});
