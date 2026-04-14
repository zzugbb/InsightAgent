"use client";

import { App, Button, Input } from "antd";
import { useMemo, useState } from "react";

import { ApiError, apiPutJson } from "../../../lib/api-client";
import { useMessages } from "../../../lib/preferences-context";
import type { SettingsSummary } from "../workbench/types";
import styles from "./onboarding-setup.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type OnboardingSetupProps = {
  initialSettings: SettingsSummary | null;
  onComplete: () => void;
  onLogout: () => void;
};

type SettingsUpdateResponse = {
  mode: string;
  provider: string;
  model: string;
  api_key_configured: boolean;
  base_url_configured: boolean;
  database_locator: string;
};

function parseSetupError(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : fallback;
  }
  if (!error.bodySnippet) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(error.bodySnippet) as { detail?: string };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export function OnboardingSetup({
  initialSettings,
  onComplete,
  onLogout,
}: OnboardingSetupProps) {
  const { message } = App.useApp();
  const t = useMessages();
  const auth = t.auth;
  const [provider, setProvider] = useState(initialSettings?.provider ?? "openai");
  const [model, setModel] = useState(initialSettings?.model ?? "gpt-4o-mini");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);

  const canSubmit = useMemo(
    () => Boolean(provider.trim() && model.trim() && apiKey.trim()),
    [apiKey, model, provider],
  );

  async function handleSubmit() {
    if (!canSubmit || submitting) {
      return;
    }
    setSubmitting(true);
    setErrorText(null);
    try {
      await apiPutJson<SettingsUpdateResponse>(`${API_BASE_URL}/api/settings`, {
        mode: "remote",
        provider: provider.trim(),
        model: model.trim(),
        base_url: baseUrl.trim() || null,
        api_key: apiKey.trim(),
      });
      message.success(auth.onboardingSaved);
      onComplete();
    } catch (error) {
      setErrorText(parseSetupError(error, auth.requestFailedRetry));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.shell}>
      <section className={styles.hero}>
        <p className={styles.kicker}>INSIGHTAGENT</p>
        <h1 className={styles.title}>{auth.onboardingTitle}</h1>
        <p className={styles.lead}>{auth.onboardingLead}</p>
      </section>
      <section className={styles.form}>
        <label className={styles.label} htmlFor="onboarding-provider">
          {auth.onboardingProviderLabel}
        </label>
        <Input
          id="onboarding-provider"
          placeholder={auth.onboardingProviderPlaceholder}
          value={provider}
          onChange={(event) => setProvider(event.target.value)}
        />

        <label className={styles.label} htmlFor="onboarding-model">
          {auth.onboardingModelLabel}
        </label>
        <Input
          id="onboarding-model"
          placeholder={auth.onboardingModelPlaceholder}
          value={model}
          onChange={(event) => setModel(event.target.value)}
        />

        <label className={styles.label} htmlFor="onboarding-base-url">
          {auth.onboardingBaseUrlLabel}
        </label>
        <Input
          id="onboarding-base-url"
          placeholder={auth.onboardingBaseUrlPlaceholder}
          value={baseUrl}
          onChange={(event) => setBaseUrl(event.target.value)}
        />

        <label className={styles.label} htmlFor="onboarding-api-key">
          {auth.onboardingApiKeyLabel}
        </label>
        <Input.Password
          id="onboarding-api-key"
          placeholder={auth.onboardingApiKeyPlaceholder}
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          onPressEnter={() => {
            void handleSubmit();
          }}
        />

        {errorText ? <p className={styles.errorText}>{errorText}</p> : null}

        <div className={styles.actions}>
          <Button
            type="primary"
            size="large"
            loading={submitting}
            disabled={!canSubmit}
            onClick={() => {
              void handleSubmit();
            }}
          >
            {submitting ? auth.onboardingSaving : auth.onboardingSave}
          </Button>
          <Button onClick={onLogout}>{auth.onboardingLogout}</Button>
        </div>
      </section>
    </main>
  );
}
