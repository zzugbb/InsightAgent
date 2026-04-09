"use client";

import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getMessages } from "./i18n";
import type { Locale } from "./i18n/types";
import {
  applyPrimaryColorToDocument,
  DEFAULT_PRIMARY_HEX,
  normalizePrimaryHex,
  readStoredPrimaryColor,
} from "./theme-primary";
import {
  LOCALE_STORAGE_KEY,
  PRIMARY_COLOR_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "./storage-keys";

export type Theme = "light" | "dark";

export { LOCALE_STORAGE_KEY, PRIMARY_COLOR_STORAGE_KEY, THEME_STORAGE_KEY };

type PreferencesContextValue = {
  theme: Theme;
  setTheme: (t: Theme) => void;
  /** 主题主色，如 #22c55e 或带透明 #RRGGBBAA */
  primaryColor: string;
  setPrimaryColor: (hex: string) => void;
  locale: Locale;
  setLocale: (l: Locale) => void;
  localeTag: "zh-CN" | "en-US";
  messages: ReturnType<typeof getMessages>;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function readStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(THEME_STORAGE_KEY);
  if (v === "light" || v === "dark") return v;
  return null;
}

function readStoredLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  const v = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (v === "zh" || v === "en") return v;
  return null;
}

function readThemeFromDom(): Theme | null {
  if (typeof document === "undefined") return null;
  const v = document.documentElement.getAttribute("data-theme");
  if (v === "light" || v === "dark") return v;
  return null;
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [primaryColor, setPrimaryColorState] = useState(DEFAULT_PRIMARY_HEX);
  const [locale, setLocaleState] = useState<Locale>("zh");

  useLayoutEffect(() => {
    const t =
      readThemeFromDom() ??
      readStoredTheme() ??
      (window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark");
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);

    const p = readStoredPrimaryColor();
    setPrimaryColorState(p);
    applyPrimaryColorToDocument(p);

    const l =
      readStoredLocale() ??
      (navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");
    setLocaleState(l);
    document.documentElement.lang = l === "zh" ? "zh-CN" : "en-US";
  }, []);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
    document.documentElement.lang = next === "zh" ? "zh-CN" : "en-US";
  }, []);

  const setPrimaryColor = useCallback((hex: string) => {
    const next = normalizePrimaryHex(hex) ?? DEFAULT_PRIMARY_HEX;
    setPrimaryColorState(next);
    localStorage.setItem(PRIMARY_COLOR_STORAGE_KEY, next);
    applyPrimaryColorToDocument(next);
  }, []);

  const value = useMemo<PreferencesContextValue>(
    () => ({
      theme,
      setTheme,
      primaryColor,
      setPrimaryColor,
      locale,
      setLocale,
      localeTag: locale === "zh" ? "zh-CN" : "en-US",
      messages: getMessages(locale),
    }),
    [theme, setTheme, primaryColor, setPrimaryColor, locale, setLocale],
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return ctx;
}

export function useMessages() {
  return usePreferences().messages;
}
