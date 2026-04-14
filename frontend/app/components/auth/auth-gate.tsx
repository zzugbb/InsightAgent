"use client";

import { App, Button, Input, Spin, Tabs } from "antd";
import { LogOut, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  apiJson,
  apiPostJson,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from "../../../lib/api-client";
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

function parseAuthError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : "请求失败，请稍后重试。";
  }
  if (!error.bodySnippet) {
    return `请求失败（${error.status}）`;
  }
  try {
    const parsed = JSON.parse(error.bodySnippet) as { detail?: string };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) {
      return parsed.detail;
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
  const [user, setUser] = useState<AuthUser | null>(null);
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);

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
        if (!cancelled) {
          setStatus("anonymous");
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onAuthExpired() {
      clearAuthToken();
      queryClient.clear();
      setUser(null);
      setStatus("anonymous");
      setPassword("");
      message.warning("登录已过期，请重新登录。");
    }
    window.addEventListener("insightagent:auth-expired", onAuthExpired);
    return () => {
      window.removeEventListener("insightagent:auth-expired", onAuthExpired);
    };
  }, [message, queryClient]);

  const canSubmit = useMemo(() => {
    if (!email.trim() || !password.trim()) {
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
    queryClient.clear();
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
          面向面试展示与真实部署的 AI Agent 项目。对话、执行轨迹、RAG、成本统计统一在一个工作界面完成闭环。
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
          <span>账号鉴权入口</span>
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
                placeholder="面试展示账号"
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

        <p className={styles.formFootnote}>
          当前用户：{user?.display_name || user?.email || "未登录"}
        </p>
      </section>
    </main>
  );
}
