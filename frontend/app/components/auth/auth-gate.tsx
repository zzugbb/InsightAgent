"use client";

import { App, Button, Input, Spin, Tabs } from "antd";
import { LogOut, ShieldCheck } from "lucide-react";
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

function parseAuthError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : "请求失败，请稍后重试。";
  }
  if (!error.bodySnippet) {
    return `请求失败（${error.status}）`;
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
        return "请输入有效的邮箱地址。";
      }
      if (typeof first?.msg === "string" && first.msg.trim()) {
        return first.msg;
      }
    }
  } catch {
    // ignore
  }
  return `请求失败（${error.status}）`;
}

export function AuthGate() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [, setUser] = useState<AuthUser | null>(null);
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
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
      message.warning("登录已过期，请重新登录。");
    }
    window.addEventListener("insightagent:auth-expired", onAuthExpired);
    return () => {
      window.removeEventListener("insightagent:auth-expired", onAuthExpired);
    };
  }, [message, resetUserScopedClientState]);

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
      setErrorText("请输入有效的邮箱地址。");
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
      message.success(mode === "login" ? "登录成功" : "注册成功，已自动登录");
    } catch (error) {
      setErrorText(parseAuthError(error));
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
    message.info("已退出登录");
  }

  if (status === "checking") {
    return (
      <main className={styles.loadingShell}>
        <Spin size="large" />
        <p className={styles.loadingText}>正在校验登录状态...</p>
      </main>
    );
  }

  if (status === "authenticated") {
    return (
      <div className={styles.workspaceShell}>
        <button type="button" className={styles.logoutButton} onClick={handleLogout}>
          <LogOut size={16} />
          退出
        </button>
        <Workbench />
      </div>
    );
  }

  return (
    <main className={styles.authShell}>
      <section className={styles.heroArea}>
        <div className={styles.heroGlow} />
        <p className={styles.eyebrow}>INSIGHTAGENT</p>
        <h1 className={styles.heroTitle}>可观测 Agent 工作台</h1>
        <p className={styles.heroDesc}>
          聚焦对话、执行轨迹、RAG 与成本统计的一体化智能体工作台，让调试、观测与协作在一个界面内闭环。
        </p>
        <ul className={styles.heroList}>
          <li>SSE 实时流式 + Trace 可回放</li>
          <li>Memory 与 RAG 双上下文能力</li>
          <li>任务级 Token / Cost 可追踪</li>
        </ul>
      </section>

      <section className={styles.formArea}>
        <div className={styles.formHeader}>
          <ShieldCheck size={18} />
          <span>登录账号</span>
        </div>

        <Tabs
          activeKey={mode}
          onChange={(key) => {
            setMode(key === "register" ? "register" : "login");
            setErrorText(null);
          }}
          items={[
            { key: "login", label: "登录" },
            { key: "register", label: "注册" },
          ]}
        />

        <div className={styles.fieldStack}>
          <label className={styles.label} htmlFor="auth-email">
            邮箱
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
                昵称（可选）
              </label>
              <Input
                id="auth-display-name"
                autoComplete="nickname"
                placeholder="你的昵称"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </>
          ) : null}

          <label className={styles.label} htmlFor="auth-password">
            密码
          </label>
          <Input.Password
            id="auth-password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={mode === "register" ? "至少 8 位" : "输入账号密码"}
            value={password}
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
            {mode === "login" ? "进入工作台" : "创建账号并进入"}
          </Button>
        </div>

      </section>
    </main>
  );
}
