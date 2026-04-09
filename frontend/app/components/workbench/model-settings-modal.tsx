"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { apiJson, apiPutJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useFocusTrap } from "../../../lib/hooks/use-focus-trap";
import { useMessages } from "../../../lib/preferences-context";

import type { SettingsFormState, SettingsSummary } from "./types";
import { API_BASE_URL } from "./utils";

const DEFAULT_FORM: SettingsFormState = {
  mode: "mock",
  provider: "mock",
  model: "mock-gpt",
  base_url: "",
  api_key: "",
};

type ModelSettingsModalProps = {
  open: boolean;
  onClose: () => void;
  /** 关闭后恢复焦点到设置按钮 */
  triggerRef?: RefObject<HTMLButtonElement | null>;
};

export function ModelSettingsModal({
  open,
  onClose,
  triggerRef,
}: ModelSettingsModalProps) {
  const t = useMessages();
  const queryClient = useQueryClient();
  const panelRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [form, setForm] = useState<SettingsFormState>(DEFAULT_FORM);
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => setMounted(true), []);

  const { data, isLoading, error, isError } = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`),
  });

  useEffect(() => {
    if (data) {
      setForm({
        mode: data.mode,
        provider: data.provider,
        model: data.model,
        base_url: "",
        api_key: "",
      });
    }
  }, [data]);

  useEffect(() => {
    if (isError && error) {
      const u = toUserFacingError(error, t.errors);
      setBanner(u.banner + (u.hint ? ` ${u.hint}` : ""));
    }
  }, [isError, error, t.errors]);

  useEffect(() => {
    if (!open) {
      setBanner(null);
      return;
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useFocusTrap(open, panelRef, triggerRef);

  const saveMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiPutJson<SettingsSummary>(`${API_BASE_URL}/api/settings`, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      setForm((c) => ({ ...c, api_key: "" }));
      setBanner(null);
    },
    onError: (e) => {
      const u = toUserFacingError(e, t.errors);
      setBanner(u.banner);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveMutation.mutate({
      mode: form.mode,
      provider: form.provider,
      model: form.model,
      base_url: form.base_url || null,
      api_key: form.api_key || null,
    });
  }

  if (!mounted || !open) {
    return null;
  }

  return createPortal(
    <div className="model-settings-modal-root" role="presentation">
      <button
        type="button"
        className="model-settings-modal-scrim"
        aria-label={t.settings.close}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className="model-settings-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-settings-title"
      >
        <header className="model-settings-modal-head">
          <div>
            <h2 id="model-settings-title">{t.settings.title}</h2>
            <p className="model-settings-modal-lead">{t.settings.modalSubtitle}</p>
          </div>
          <button
            type="button"
            className="ghost-button model-settings-modal-close"
            onClick={onClose}
            aria-label={t.settings.close}
          >
            <X size={20} aria-hidden />
          </button>
        </header>

        {banner ? (
          <div className="api-banner model-settings-banner" role="alert">
            <p>{banner}</p>
            <button
              type="button"
              className="api-banner-dismiss"
              onClick={() => setBanner(null)}
            >
              {t.settings.close}
            </button>
          </div>
        ) : null}

        {isLoading ? (
          <p className="settings-page-loading">{t.settings.loading}</p>
        ) : (
          <form className="settings-form model-settings-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>{t.settings.fieldMode}</span>
              <select
                value={form.mode}
                onChange={(e) =>
                  setForm((c) => ({ ...c, mode: e.target.value }))
                }
              >
                <option value="mock">mock</option>
                <option value="remote">remote</option>
              </select>
            </label>
            <label className="field">
              <span>{t.settings.fieldProvider}</span>
              <input
                value={form.provider}
                onChange={(e) =>
                  setForm((c) => ({ ...c, provider: e.target.value }))
                }
                placeholder="mock"
              />
            </label>
            <label className="field">
              <span>{t.settings.fieldModel}</span>
              <input
                value={form.model}
                onChange={(e) =>
                  setForm((c) => ({ ...c, model: e.target.value }))
                }
                placeholder="mock-gpt"
              />
            </label>
            <label className="field">
              <span>{t.settings.fieldBaseUrl}</span>
              <input
                value={form.base_url}
                onChange={(e) =>
                  setForm((c) => ({ ...c, base_url: e.target.value }))
                }
                placeholder={t.settings.optionalPlaceholder}
              />
            </label>
            <label className="field">
              <span>{t.settings.fieldApiKey}</span>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) =>
                  setForm((c) => ({ ...c, api_key: e.target.value }))
                }
                placeholder={
                  data?.api_key_configured
                    ? t.settings.apiKeyConfiguredKeep
                    : t.settings.apiKeyOptionalMock
                }
              />
            </label>
            <button
              className="primary-button"
              type="submit"
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? t.settings.saving : t.settings.save}
            </button>
          </form>
        )}

        {data ? (
          <div className="context-grid compact settings-page-meta model-settings-meta">
            <span>{t.settings.metaProvider}</span>
            <strong>{data.provider}</strong>
            <span>{t.settings.metaModel}</span>
            <strong>{data.model}</strong>
            <span>{t.settings.metaApiKey}</span>
            <strong>
              {data.api_key_configured
                ? t.settings.metaConfigured
                : t.settings.metaNotConfigured}
            </strong>
            <span>{t.settings.metaSqlite}</span>
            <strong>{data.sqlite_path}</strong>
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
