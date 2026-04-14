"use client";

import { App, Button, ColorPicker, Input, Popover, Segmented, Spin, Tabs } from "antd";
import { Check, Eye, EyeOff, Palette, Settings2, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  authFetch,
  apiJson,
  apiPostJson,
  clearAuthSessionStorage,
  getAuthToken,
  getRefreshToken,
  setAuthSessionId,
  setAuthToken,
  setRefreshToken,
} from "../../../lib/api-client";
import { useChatStreamStore } from "../../../lib/stores/chat-stream-store";
import { useMessages, usePreferences } from "../../../lib/preferences-context";
import type { Messages } from "../../../lib/i18n/types";
import { hexKeyForCompare, PRESET_SWATCHES } from "../../../lib/theme-primary";
import { Workbench } from "../workbench";
import { OnboardingSetup } from "./onboarding-setup";
import type { SettingsSummary } from "../workbench/types";
import styles from "./auth-gate.module.css";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type AuthUser = {
  id: string;
  email: string;
  display_name?: string | null;
  created_at: string;
  updated_at: string;
};

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  session_id: string;
  token_type: string;
  user: AuthUser;
};

type AuthMode = "login" | "register";
type AuthStatus = "checking" | "anonymous" | "authenticated";

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function parseAuthError(error: unknown, messages: Messages["auth"]): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : messages.requestFailedRetry;
  }
  if (!error.bodySnippet) {
    return messages.requestFailedWithStatus(error.status);
  }
  try {
    const parsed = JSON.parse(error.bodySnippet) as {
      detail?: string | Array<{ loc?: unknown[]; msg?: string; type?: string }>;
    };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      const first = parsed.detail[0];
      const loc = Array.isArray(first?.loc) ? first.loc.map(String) : [];
      if (loc.includes("email")) {
        return messages.invalidEmail;
      }
      if (typeof first?.msg === "string" && first.msg.trim()) {
        return first.msg;
      }
    }
  } catch {
    // ignore
  }
  return messages.requestFailedWithStatus(error.status);
}

export function AuthGate() {
  const { message } = App.useApp();
  const messages = useMessages();
  const { theme, setTheme, locale, setLocale, primaryColor, setPrimaryColor } =
    usePreferences();
  const authMessages = messages.auth;
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [, setUser] = useState<AuthUser | null>(null);
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsSummary | null>(null);

  const resetUserScopedClientState = useCallback(() => {
    queryClient.clear();
    const streamStore = useChatStreamStore.getState();
    streamStore.resetStreamUi();
    streamStore.setIsStreaming(false);
  }, [queryClient]);

  const syncOnboardingRequirement = useCallback(async (): Promise<void> => {
    try {
      const settings = await apiJson<SettingsSummary>(`${API_BASE_URL}/api/settings`);
      setSettingsSnapshot(settings);
      setNeedsOnboarding(!settings.api_key_configured);
    } catch {
      // 若设置读取失败，为避免用户直接误入工作台，这里保守进入引导页
      setSettingsSnapshot(null);
      setNeedsOnboarding(true);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const hasAuthState = Boolean(getAuthToken() || getRefreshToken());
      if (!hasAuthState) {
        if (!cancelled) {
          setStatus("anonymous");
        }
        return;
      }
      try {
        const me = await apiJson<AuthUser>(`${API_BASE_URL}/api/auth/me`);
        if (cancelled) {
          return;
        }
        setUser(me);
        await syncOnboardingRequirement();
        if (cancelled) {
          return;
        }
        setStatus("authenticated");
      } catch {
        clearAuthSessionStorage();
        resetUserScopedClientState();
        setNeedsOnboarding(false);
        setSettingsSnapshot(null);
        if (!cancelled) {
          setStatus("anonymous");
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [resetUserScopedClientState, syncOnboardingRequirement]);

  useEffect(() => {
    function onAuthExpired() {
      clearAuthSessionStorage();
      resetUserScopedClientState();
      setUser(null);
      setNeedsOnboarding(false);
      setSettingsSnapshot(null);
      setStatus("anonymous");
      setPassword("");
      message.warning(authMessages.expiredRelogin);
    }
    window.addEventListener("insightagent:auth-expired", onAuthExpired);
    return () => {
      window.removeEventListener("insightagent:auth-expired", onAuthExpired);
    };
  }, [authMessages.expiredRelogin, message, resetUserScopedClientState]);

  const canSubmit = useMemo(() => {
    if (!email.trim() || !password.trim()) {
      return false;
    }
    if (!isValidEmail(email)) {
      return false;
    }
    if (mode === "register" && password.trim().length < 8) {
      return false;
    }
    return true;
  }, [email, mode, password]);

  async function handleSubmit() {
    if (!canSubmit || submitting) {
      return;
    }
    if (!isValidEmail(email)) {
      setErrorText(authMessages.invalidEmail);
      return;
    }
    setSubmitting(true);
    setErrorText(null);
    try {
      const payload =
        mode === "login"
          ? {
              email: email.trim(),
              password,
            }
          : {
              email: email.trim(),
              password,
              display_name: displayName.trim() || null,
            };
      const endpoint = mode === "login" ? "login" : "register";
      const response = await apiPostJson<AuthResponse>(
        `${API_BASE_URL}/api/auth/${endpoint}`,
        payload,
      );
      resetUserScopedClientState();
      setAuthToken(response.access_token);
      setRefreshToken(response.refresh_token);
      setAuthSessionId(response.session_id);
      setUser(response.user);
      await syncOnboardingRequirement();
      setStatus("authenticated");
      setPassword("");
      message.success(
        mode === "login"
          ? authMessages.loginSuccess
          : authMessages.registerSuccessAutoLogin,
      );
    } catch (error) {
      setErrorText(parseAuthError(error, authMessages));
    } finally {
      setSubmitting(false);
    }
  }

  const handleLogout = useCallback(() => {
    const refreshToken = getRefreshToken();
    void (async () => {
      try {
        if (refreshToken) {
          await authFetch(`${API_BASE_URL}/api/auth/logout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
        }
      } catch {
        // logout 是幂等操作，这里忽略网络或鉴权失败，继续本地清理
      } finally {
        clearAuthSessionStorage();
        resetUserScopedClientState();
        setUser(null);
        setNeedsOnboarding(false);
        setSettingsSnapshot(null);
        setStatus("anonymous");
        setPassword("");
        message.info(authMessages.logoutSuccess);
      }
    })();
  }, [authMessages.logoutSuccess, message, resetUserScopedClientState]);

  if (status === "checking") {
    return (
      <main className={styles.loadingShell}>
        <Spin size="large" />
        <p className={styles.loadingText}>{authMessages.checkingStatus}</p>
      </main>
    );
  }

  if (status === "authenticated") {
    if (needsOnboarding) {
      return (
        <OnboardingSetup
          initialSettings={settingsSnapshot}
          onComplete={() => {
            setNeedsOnboarding(false);
          }}
          onLogout={handleLogout}
        />
      );
    }
    return <Workbench onLogout={handleLogout} />;
  }

  const settingsContent = (
    <div className={styles.settingsPopover}>
      <p className={styles.settingsTitle}>{authMessages.settingsTitle}</p>
      <div className={styles.settingsSection}>
        <span className={styles.settingsLabel}>{messages.settings.languageLabel}</span>
        <Segmented
          block
          size="small"
          value={locale}
          options={[
            { label: messages.settings.languageZh, value: "zh" },
            { label: messages.settings.languageEn, value: "en" },
          ]}
          onChange={(value) => {
            setLocale(value === "en" ? "en" : "zh");
          }}
        />
      </div>
      <div className={styles.settingsSection}>
        <span className={styles.settingsLabel}>{messages.settings.themeLabel}</span>
        <Segmented
          block
          size="small"
          value={theme}
          options={[
            { label: messages.settings.themeDark, value: "dark" },
            { label: messages.settings.themeLight, value: "light" },
          ]}
          onChange={(value) => {
            setTheme(value === "light" ? "light" : "dark");
          }}
        />
      </div>
      <div className={styles.settingsSection}>
        <span className={styles.settingsLabel}>{messages.sidebar.menuAccent}</span>
        <div className={styles.swatches}>
          {PRESET_SWATCHES.map((hex) => {
            const active = hexKeyForCompare(primaryColor) === hexKeyForCompare(hex);
            return (
              <button
                key={hex}
                type="button"
                className={`${styles.swatch}${active ? ` ${styles.swatchActive}` : ""}`}
                style={{ backgroundColor: hex }}
                onClick={() => setPrimaryColor(hex)}
                aria-label={hex}
                aria-pressed={active}
              >
                {active ? <Check size={12} strokeWidth={3} aria-hidden /> : null}
              </button>
            );
          })}
        </div>
        <div className={styles.customColorRow}>
          <Palette size={14} strokeWidth={1.75} aria-hidden />
          <ColorPicker
            value={primaryColor}
            onChangeComplete={(c) => setPrimaryColor(c.toHexString())}
            format="hex"
            showText
            disabledAlpha={false}
          />
        </div>
      </div>
    </div>
  );

  return (
    <main className={styles.authShell}>
      <div className={styles.topActions}>
        <Popover
          trigger="click"
          placement="bottomRight"
          open={settingsOpen}
          onOpenChange={setSettingsOpen}
          content={settingsContent}
          destroyOnHidden
        >
          <Button type="text" className={styles.settingsBtn} icon={<Settings2 size={16} />}>
            {authMessages.settingsButton}
          </Button>
        </Popover>
      </div>
      <section className={styles.heroArea}>
        <div className={styles.heroGlow} />
        <p className={styles.eyebrow}>INSIGHTAGENT</p>
        <h1 className={styles.heroTitle}>{authMessages.heroTitle}</h1>
        <p className={styles.heroDesc}>{authMessages.heroDesc}</p>
        <ul className={styles.heroList}>
          <li>{authMessages.heroFeatureSseTrace}</li>
          <li>{authMessages.heroFeatureSessionTaskTrace}</li>
          <li>{authMessages.heroFeatureMemoryRag}</li>
          <li>{authMessages.heroFeatureTokenCost}</li>
        </ul>
      </section>

      <section className={styles.formArea}>
        <div className={styles.formHeader}>
          <ShieldCheck size={18} />
          <span>{authMessages.formTitle}</span>
        </div>

        <Tabs
          activeKey={mode}
          onChange={(key) => {
            setMode(key === "register" ? "register" : "login");
            setErrorText(null);
          }}
          items={[
            { key: "login", label: authMessages.tabLogin },
            { key: "register", label: authMessages.tabRegister },
          ]}
        />

        <div className={styles.fieldStack}>
          <label className={styles.label} htmlFor="auth-email">
            {authMessages.emailLabel}
          </label>
          <Input
            id="auth-email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />

          {mode === "register" ? (
            <>
              <label className={styles.label} htmlFor="auth-display-name">
                {authMessages.displayNameOptionalLabel}
              </label>
              <Input
                id="auth-display-name"
                autoComplete="nickname"
                placeholder={authMessages.displayNamePlaceholder}
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </>
          ) : null}

          <label className={styles.label} htmlFor="auth-password">
            {authMessages.passwordLabel}
          </label>
          <Input.Password
            id="auth-password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={
              mode === "register"
                ? authMessages.passwordPlaceholderRegister
                : authMessages.passwordPlaceholderLogin
            }
            value={password}
            visibilityToggle={{
              visible: passwordVisible,
              onVisibleChange: setPasswordVisible,
            }}
            iconRender={(visible) =>
              visible ? (
                <Eye size={16} strokeWidth={2} className={styles.passwordEyeIcon} />
              ) : (
                <EyeOff size={16} strokeWidth={2} className={styles.passwordEyeIcon} />
              )
            }
            onChange={(event) => setPassword(event.target.value)}
            onPressEnter={() => {
              void handleSubmit();
            }}
          />

          {errorText ? <p className={styles.errorText}>{errorText}</p> : null}

          <Button
            type="primary"
            block
            size="large"
            loading={submitting}
            disabled={!canSubmit}
            onClick={() => {
              void handleSubmit();
            }}
          >
            {mode === "login"
              ? authMessages.submitLogin
              : authMessages.submitRegister}
          </Button>
        </div>

      </section>
    </main>
  );
}
