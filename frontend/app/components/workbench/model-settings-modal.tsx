"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
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
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SettingsFormState>(DEFAULT_FORM);
  const [lastRemoteForm, setLastRemoteForm] = useState<RemoteFormState>({
    provider: "",
    model: "",
    base_url: "",
    api_key: "",
  });
  const [banner, setBanner] = useState<string | null>(null);
  const [bannerKind, setBannerKind] = useState<"error" | "success">("error");

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
    if (data.mode === "remote") {
      setLastRemoteForm({
        provider: nextForm.provider,
        model: nextForm.model,
        base_url: nextForm.base_url,
        api_key: "",
      });
    }
  }, [data, open]);

  useEffect(() => {
    if (isError && error) {
      const u = toUserFacingError(error, t.errors);
      setBanner(u.banner + (u.hint ? ` ${u.hint}` : ""));
      setBannerKind("error");
    }
  }, [isError, error, t.errors]);

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
      setBannerKind("error");
    },
  });

  const validateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiPostJson<SettingsValidateResponse>(`${API_BASE_URL}/api/settings/validate`, body),
    onSuccess: (data) => {
      if (data.ok) {
        setBanner(`${t.settings.validatePass}: ${data.message}`);
        setBannerKind("success");
        return;
      }
      setBanner(
        `${t.settings.validateFail}: ${data.error || data.message}`,
      );
      setBannerKind("error");
    },
    onError: (e) => {
      const u = toUserFacingError(e, t.errors);
      setBanner(`${t.settings.validateFail}: ${u.banner}`);
      setBannerKind("error");
    },
  });

  useEffect(() => {
    if (!open) {
      setForm(DEFAULT_FORM);
      setLastRemoteForm({
        provider: "",
        model: "",
        base_url: "",
        api_key: "",
      });
    }
    setBanner(null);
    setBannerKind("error");
  }, [open]);

  function setRemoteField(
    field: keyof RemoteFormState,
    value: string,
  ) {
    setForm((current) => ({ ...current, [field]: value }));
    setLastRemoteForm((current) => ({ ...current, [field]: value }));
  }

  function handleModeChange(nextMode: string) {
    if (nextMode === form.mode) {
      return;
    }
    if (nextMode === "mock") {
      if (form.mode === "remote") {
        setLastRemoteForm({
          provider: form.provider,
          model: form.model,
          base_url: form.base_url,
          api_key: form.api_key,
        });
      }
      setForm(DEFAULT_FORM);
      return;
    }

    const restoreFromData: RemoteFormState = {
      provider: data?.mode === "remote" ? data.provider : "",
      model: data?.mode === "remote" ? data.model : "",
      base_url: data?.mode === "remote" ? (data.base_url ?? "") : "",
      api_key: "",
    };
    const hasDraft =
      Boolean(lastRemoteForm.provider.trim()) ||
      Boolean(lastRemoteForm.model.trim()) ||
      Boolean(lastRemoteForm.base_url.trim()) ||
      Boolean(lastRemoteForm.api_key.trim());
    const restored = hasDraft ? lastRemoteForm : restoreFromData;
    setForm({
      mode: "remote",
      provider: restored.provider,
      model: restored.model,
      base_url: restored.base_url,
      api_key: restored.api_key,
    });
  }

  function submitForm() {
    const isMockMode = form.mode === "mock";
    saveMutation.mutate({
      mode: form.mode,
      provider: isMockMode ? "mock" : form.provider,
      model: isMockMode ? "mock-gpt" : form.model,
      base_url: isMockMode ? null : form.base_url || null,
      api_key: isMockMode ? null : form.api_key || null,
    });
  }

  function validateForm() {
    const isMockMode = form.mode === "mock";
    validateMutation.mutate({
      mode: form.mode,
      provider: isMockMode ? "mock" : form.provider,
      model: isMockMode ? "mock-gpt" : form.model,
      base_url: isMockMode ? null : form.base_url || null,
      api_key: isMockMode ? null : form.api_key || null,
    });
  }

  const isRemoteMode = form.mode === "remote";
  const summaryProvider = isRemoteMode ? form.provider || "—" : "mock";
  const summaryModel = isRemoteMode ? form.model || "—" : "mock-gpt";
  const summaryBaseUrl = isRemoteMode ? form.base_url || "—" : "";
  const summaryApiConfigured = isRemoteMode
    ? Boolean(form.api_key.trim()) || Boolean(data?.api_key_configured)
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
      {banner ? (
        <Alert
          type={bannerKind}
          showIcon
          closable
          title={banner}
          onClose={() => setBanner(null)}
          style={{ marginBottom: 16 }}
        />
      ) : null}
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
                value={form.provider}
                onChange={(e) => setRemoteField("provider", e.target.value)}
                placeholder="openai-compatible"
              />
            ) : (
              <Input value="mock" disabled />
            )}
          </Form.Item>
          <Form.Item label={t.settings.fieldModel}>
            {isRemoteMode ? (
              <Input
                autoComplete="off"
                name="model-name"
                data-1p-ignore="true"
                data-lpignore="true"
                value={form.model}
                onChange={(e) => setRemoteField("model", e.target.value)}
                placeholder="gpt-4o-mini / deepseek-chat / glm-4.5"
              />
            ) : (
              <Input value="mock-gpt" disabled />
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
                  value={form.base_url}
                  onChange={(e) => setRemoteField("base_url", e.target.value)}
                  placeholder={t.settings.optionalPlaceholder}
                />
              </Form.Item>
              <Form.Item label={t.settings.fieldApiKey}>
                <Input.Password
                  autoComplete="new-password"
                  name="model-api-key"
                  data-1p-ignore="true"
                  data-lpignore="true"
                  value={form.api_key}
                  onChange={(e) => setRemoteField("api_key", e.target.value)}
                  placeholder={
                    data?.api_key_configured
                      ? t.settings.apiKeyConfiguredKeep
                      : t.settings.apiKeyOptionalMock
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
              >
                {saveMutation.isPending ? t.settings.saving : t.settings.save}
              </Button>
              <Button
                onClick={validateForm}
                loading={validateMutation.isPending}
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
                <code className="model-settings-database-path">{summaryBaseUrl}</code>
              </Descriptions.Item>
              <Descriptions.Item label={t.settings.metaApiKey}>
                {summaryApiConfigured
                  ? t.settings.metaConfigured
                  : t.settings.metaNotConfigured}
              </Descriptions.Item>
            </>
          ) : null}
          <Descriptions.Item label={t.settings.metaDatabase}>
            <code className="model-settings-database-path">{data.database_locator}</code>
          </Descriptions.Item>
        </Descriptions>
      ) : null}
    </Modal>
  );
}
