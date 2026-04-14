"use client";

import { App, Button, Input, Spin, Tabs } from "antd";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  apiJson,
  apiPostJson,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from "../../../lib/api-client";
import { useChatStreamStore } from "../../../lib/stores/chat-stream-store";
import { useMessages } from "../../../lib/preferences-context";
import type { Messages } from "../../../lib/i18n/types";
import { Workbench } from "../workbench";
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

  const resetUserScopedClientState = useCallback(() => {
    queryClient.clear();
    const streamStore = useChatStreamStore.getState();
    streamStore.resetStreamUi();
    streamStore.setIsStreaming(false);
  }, [queryClient]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const token = getAuthToken();
      if (!token) {
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
        setStatus("authenticated");
      } catch {
        clearAuthToken();
        resetUserScopedClientState();
        if (!cancelled) {
          setStatus("anonymous");
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [resetUserScopedClientState]);

  useEffect(() => {
    function onAuthExpired() {
      clearAuthToken();
      resetUserScopedClientState();
      setUser(null);
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
      setUser(response.user);
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

  function handleLogout() {
    clearAuthToken();
    resetUserScopedClientState();
    setUser(null);
    setStatus("anonymous");
    setPassword("");
    message.info(authMessages.logoutSuccess);
  }

  if (status === "checking") {
    return (
      <main className={styles.loadingShell}>
        <Spin size="large" />
        <p className={styles.loadingText}>{authMessages.checkingStatus}</p>
      </main>
    );
  }

  if (status === "authenticated") {
    return <Workbench onLogout={handleLogout} />;
  }

  return (
    <main className={styles.authShell}>
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
