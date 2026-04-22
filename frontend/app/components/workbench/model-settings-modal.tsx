"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Descriptions,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Typography,
} from "antd";
import { useEffect, useState, type RefObject } from "react";

import { apiJson, apiPostJson, apiPutJson } from "../../../lib/api-client";
import { toUserFacingError } from "../../../lib/errors";
import { useMessages } from "../../../lib/preferences-context";

import type {
  SettingsFormState,
  SettingsSummary,
  SettingsValidateResponse,
} from "./types";
import { API_BASE_URL } from "./utils";

const DEFAULT_FORM: SettingsFormState = {
  mode: "mock",
  provider: "mock",
  model: "mock-gpt",
  base_url: "",
  api_key: "",
};

type RemoteFormState = Omit<SettingsFormState, "mode">;

type ModelSettingsModalProps = {
  open: boolean;
  onClose: () => void;
  triggerRef?: RefObject<HTMLButtonElement | null>;
};

export function ModelSettingsModal({
  open,
  onClose,
}: ModelSettingsModalProps) {
  const t = useMessages();
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SettingsFormState>(DEFAULT_FORM);

  const { data, isLoading, error, isError } = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`),
  });

  useEffect(() => {
    if (!open || !data) {
      return;
    }
    const nextForm: SettingsFormState = {
      mode: data.mode,
      provider: data.provider,
      model: data.model,
      base_url: data.base_url ?? "",
      api_key: "",
    };
    setForm(nextForm);
  }, [data, open]);

  useEffect(() => {
    if (isError && error) {
      const u = toUserFacingError(error, t.errors);
      message.error(u.banner + (u.hint ? ` ${u.hint}` : ""));
    }
  }, [isError, error, t.errors, message]);

  const saveMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiPutJson<SettingsSummary>(`${API_BASE_URL}/api/settings`, body),
    onSuccess: (nextSettings) => {
      queryClient.setQueryData(["settings"], nextSettings);
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      setForm((c) => ({ ...c, api_key: "" }));
      message.success(t.settings.saveSuccess);
    },
    onError: (e) => {
      const u = toUserFacingError(e, t.errors);
      message.error(`${t.settings.saveFail}: ${u.banner}`);
    },
  });

  const validateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiPostJson<SettingsValidateResponse>(`${API_BASE_URL}/api/settings/validate`, body),
    onSuccess: (data) => {
      if (data.ok) {
        message.success(`${t.settings.validatePass}: ${data.message}`);
        return;
      }
      const code =
        typeof data.error_code === "string" && data.error_code.trim().length > 0
          ? data.error_code.trim()
          : null;
      const mapped = code ? t.settings.validateErrorByCode(code) : null;
      const reason = mapped || data.error || data.message;
      const codeSuffix = code ? ` [${code}]` : "";
      message.error(`${t.settings.validateFail}: ${reason}${codeSuffix}`);
    },
    onError: (e) => {
      const u = toUserFacingError(e, t.errors);
      message.error(`${t.settings.validateFail}: ${u.banner}`);
    },
  });

  useEffect(() => {
    if (!open) {
      setForm(DEFAULT_FORM);
    }
  }, [open]);

  function setRemoteField(
    field: keyof RemoteFormState,
    value: string,
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function handleModeChange(nextMode: string) {
    if (nextMode === form.mode) {
      return;
    }
    if (nextMode === "mock") {
      setForm(DEFAULT_FORM);
      return;
    }

    const shouldRestorePersistedRemote = data?.mode === "remote";
    setForm({
      mode: "remote",
      provider: shouldRestorePersistedRemote ? data.provider : "",
      model: shouldRestorePersistedRemote ? data.model : "",
      base_url: shouldRestorePersistedRemote ? (data.base_url ?? "") : "",
      api_key: "",
    });
  }

  function submitForm() {
    const isMockMode = form.mode === "mock";
    if (!isMockMode) {
      const missingField = getRemoteMissingFieldLabel();
      if (missingField) {
        message.error(`${missingField} ${t.settings.requiredSuffix}`);
        return;
      }
    }
    saveMutation.mutate({
      mode: form.mode,
      provider: isMockMode ? "mock" : form.provider.trim(),
      model: isMockMode ? "mock-gpt" : form.model.trim(),
      base_url: isMockMode ? null : form.base_url.trim() || null,
      api_key: isMockMode ? null : form.api_key || null,
    });
  }

  function validateForm() {
    const isMockMode = form.mode === "mock";
    if (!isMockMode) {
      const missingField = getRemoteMissingFieldLabel();
      if (missingField) {
        message.error(`${missingField} ${t.settings.requiredSuffix}`);
        return;
      }
    }
    validateMutation.mutate({
      mode: form.mode,
      provider: isMockMode ? "mock" : form.provider.trim(),
      model: isMockMode ? "mock-gpt" : form.model.trim(),
      base_url: isMockMode ? null : form.base_url.trim() || null,
      api_key: isMockMode ? null : form.api_key || null,
    });
  }

  function getRemoteMissingFieldLabel(): string | null {
    if (!form.provider.trim()) {
      return t.settings.fieldProvider;
    }
    if (!form.model.trim()) {
      return t.settings.fieldModel;
    }
    if (!form.base_url.trim()) {
      return t.settings.fieldBaseUrl;
    }
    if (!form.api_key.trim() && !data?.api_key_configured) {
      return t.settings.fieldApiKey;
    }
    return null;
  }

  const isRemoteMode = form.mode === "remote";
  const hasPersistedRemote = data?.mode === "remote";
  const summaryProvider = isRemoteMode
    ? hasPersistedRemote
      ? data.provider
      : "—"
    : "mock";
  const summaryModel = isRemoteMode
    ? hasPersistedRemote
      ? data.model
      : "—"
    : "mock-gpt";
  const summaryBaseUrl = isRemoteMode
    ? hasPersistedRemote
      ? data.base_url || "—"
      : "—"
    : "";
  const summaryApiConfigured = isRemoteMode
    ? hasPersistedRemote
      ? data.api_key_configured
      : false
    : false;

  return (
    <Modal
      title={<span id="model-settings-title">{t.settings.title}</span>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
      destroyOnHidden
      className="model-settings-ant-modal"
      styles={{ body: { paddingTop: 8 } }}
    >
      <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
        {t.settings.modalSubtitle}
      </Typography.Paragraph>
      {form.mode === "remote" ? (
        <Alert
          type="info"
          showIcon
          title={t.settings.remoteCompatibilityHint}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      {isLoading ? (
        <Typography.Paragraph type="secondary">{t.settings.loading}</Typography.Paragraph>
      ) : (
        <Form
          autoComplete="off"
          layout="vertical"
          className="model-settings-ant-form"
          onFinish={submitForm}
        >
          <Form.Item label={t.settings.fieldMode}>
            <Select
              data-testid="model-settings-mode"
              value={form.mode}
              onChange={handleModeChange}
              options={[
                { value: "mock", label: "mock" },
                { value: "remote", label: "remote" },
              ]}
            />
          </Form.Item>
          <Form.Item label={t.settings.fieldProvider}>
            {isRemoteMode ? (
              <Input
                autoComplete="off"
                name="model-provider"
                data-1p-ignore="true"
                data-lpignore="true"
                data-testid="model-settings-provider"
                value={form.provider}
                onChange={(e) => setRemoteField("provider", e.target.value)}
              />
            ) : (
              <Input value="mock" disabled data-testid="model-settings-provider" />
            )}
          </Form.Item>
          <Form.Item label={t.settings.fieldModel}>
            {isRemoteMode ? (
              <Input
                autoComplete="off"
                name="model-name"
                data-1p-ignore="true"
                data-lpignore="true"
                data-testid="model-settings-model"
                value={form.model}
                onChange={(e) => setRemoteField("model", e.target.value)}
              />
            ) : (
              <Input value="mock-gpt" disabled data-testid="model-settings-model" />
            )}
          </Form.Item>
          {isRemoteMode ? (
            <>
              <Form.Item label={t.settings.fieldBaseUrl}>
                <Input
                  autoComplete="off"
                  name="model-base-url"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-testid="model-settings-base-url"
                  value={form.base_url}
                  onChange={(e) => setRemoteField("base_url", e.target.value)}
                />
              </Form.Item>
              <Form.Item label={t.settings.fieldApiKey}>
                <Input.Password
                  autoComplete="new-password"
                  name="model-api-key"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  data-testid="model-settings-api-key"
                  value={form.api_key}
                  onChange={(e) => setRemoteField("api_key", e.target.value)}
                  placeholder={
                    data?.api_key_configured
                      ? t.settings.apiKeyConfiguredClear
                      : t.settings.apiKeyRemoteRequired
                  }
                />
              </Form.Item>
            </>
          ) : null}
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={saveMutation.isPending}
                data-testid="model-settings-save"
              >
                {saveMutation.isPending ? t.settings.saving : t.settings.save}
              </Button>
              <Button
                onClick={validateForm}
                loading={validateMutation.isPending}
                data-testid="model-settings-validate"
              >
                {validateMutation.isPending
                  ? t.settings.validating
                  : t.settings.validate}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      )}

      {data ? (
        <Descriptions
          bordered
          size="small"
          column={1}
          className="model-settings-meta-descriptions"
          style={{ marginTop: 8 }}
        >
          <Descriptions.Item label={t.settings.metaProvider}>
            {summaryProvider}
          </Descriptions.Item>
          <Descriptions.Item label={t.settings.metaModel}>
            {summaryModel}
          </Descriptions.Item>
          {isRemoteMode ? (
            <>
              <Descriptions.Item label={t.settings.metaBaseUrl}>
                {summaryBaseUrl}
              </Descriptions.Item>
              <Descriptions.Item label={t.settings.metaApiKey}>
                {summaryApiConfigured
                  ? t.settings.metaConfigured
                  : t.settings.metaNotConfigured}
              </Descriptions.Item>
            </>
          ) : null}
          <Descriptions.Item label={t.settings.metaApiBase}>
            <code>{API_BASE_URL}</code>
          </Descriptions.Item>
          <Descriptions.Item label={t.settings.metaDatabase}>
            {data.database_locator}
          </Descriptions.Item>
        </Descriptions>
      ) : null}
    </Modal>
  );
}
