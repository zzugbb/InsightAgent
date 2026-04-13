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
  const [banner, setBanner] = useState<string | null>(null);
  const [bannerKind, setBannerKind] = useState<"error" | "success">("error");

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

  function submitForm() {
    saveMutation.mutate({
      mode: form.mode,
      provider: form.provider,
      model: form.model,
      base_url: form.base_url || null,
      api_key: form.api_key || null,
    });
  }

  function validateForm() {
    validateMutation.mutate({
      mode: form.mode,
      provider: form.provider,
      model: form.model,
      base_url: form.base_url || null,
      api_key: form.api_key || null,
    });
  }

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

      {isLoading ? (
        <Typography.Paragraph type="secondary">{t.settings.loading}</Typography.Paragraph>
      ) : (
        <Form layout="vertical" className="model-settings-ant-form" onFinish={submitForm}>
          <Form.Item label={t.settings.fieldMode}>
            <Select
              value={form.mode}
              onChange={(v) => setForm((c) => ({ ...c, mode: v }))}
              options={[
                { value: "mock", label: "mock" },
                { value: "remote", label: "remote" },
              ]}
            />
          </Form.Item>
          <Form.Item label={t.settings.fieldProvider}>
            <Input
              value={form.provider}
              onChange={(e) =>
                setForm((c) => ({ ...c, provider: e.target.value }))
              }
              placeholder="mock"
            />
          </Form.Item>
          <Form.Item label={t.settings.fieldModel}>
            <Input
              value={form.model}
              onChange={(e) =>
                setForm((c) => ({ ...c, model: e.target.value }))
              }
              placeholder="mock-gpt"
            />
          </Form.Item>
          <Form.Item label={t.settings.fieldBaseUrl}>
            <Input
              value={form.base_url}
              onChange={(e) =>
                setForm((c) => ({ ...c, base_url: e.target.value }))
              }
              placeholder={t.settings.optionalPlaceholder}
            />
          </Form.Item>
          <Form.Item label={t.settings.fieldApiKey}>
            <Input.Password
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
          </Form.Item>
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
            {data.provider}
          </Descriptions.Item>
          <Descriptions.Item label={t.settings.metaModel}>
            {data.model}
          </Descriptions.Item>
          <Descriptions.Item label={t.settings.metaApiKey}>
            {data.api_key_configured
              ? t.settings.metaConfigured
              : t.settings.metaNotConfigured}
          </Descriptions.Item>
          <Descriptions.Item label={t.settings.metaSqlite}>
            <code className="model-settings-sqlite-path">{data.sqlite_path}</code>
          </Descriptions.Item>
        </Descriptions>
      ) : null}
    </Modal>
  );
}
