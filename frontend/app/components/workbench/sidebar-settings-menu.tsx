"use client";

import { ColorPicker } from "antd";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Globe,
  Monitor,
  Moon,
  Palette,
  Settings2,
  Sun,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

import {
  hexKeyForCompare,
  PRESET_SWATCHES,
} from "../../../lib/theme-primary";
import { useMessages, usePreferences } from "../../../lib/preferences-context";

import { ModelSettingsModal } from "./model-settings-modal";

type Subview = "main" | "theme" | "accent" | "language";

type PopoverPos = { left: number; bottom: number; width: number };

export function SidebarSettingsMenu() {
  const t = useMessages();
  const { theme, setTheme, primaryColor, setPrimaryColor, locale, setLocale } =
    usePreferences();
  const [open, setOpen] = useState(false);
  const [subview, setSubview] = useState<Subview>("main");
  const [modelOpen, setModelOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [popoverPos, setPopoverPos] = useState<PopoverPos | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  const layoutPopover = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPopoverPos({
      left: r.left,
      bottom: window.innerHeight - r.top + 8,
      width: r.width,
    });
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setPopoverPos(null);
      return;
    }
    layoutPopover();
    window.addEventListener("resize", layoutPopover);
    window.addEventListener("scroll", layoutPopover, true);
    return () => {
      window.removeEventListener("resize", layoutPopover);
      window.removeEventListener("scroll", layoutPopover, true);
    };
  }, [open, subview, layoutPopover]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onDocMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      setOpen(false);
      setSubview("main");
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setSubview("main");
      }
    }
    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    if (open) {
      setSubview("main");
    }
  }, [open]);

  function openModel() {
    setOpen(false);
    setSubview("main");
    setModelOpen(true);
  }

  const themeLabel =
    theme === "dark" ? t.sidebar.themeCurrentDark : t.sidebar.themeCurrentLight;
  const langLabel =
    locale === "zh" ? t.sidebar.langCurrentZh : t.sidebar.langCurrentEn;

  const primarySummary = primaryColor.toUpperCase();

  const popoverContent =
    open && mounted && popoverPos ? (
      <div
        ref={popoverRef}
        className="settings-menu-popover"
        style={{
          position: "fixed",
          left: popoverPos.left,
          bottom: popoverPos.bottom,
          width: Math.max(popoverPos.width, subview === "accent" ? 300 : 220),
          zIndex: 450,
        }}
        role="menu"
        aria-label={t.sidebar.settingsMenuLabel}
      >
        {subview === "main" ? (
          <>
            <button
              type="button"
              role="menuitem"
              className="settings-menu-row"
              onClick={() => setSubview("theme")}
            >
              {theme === "dark" ? (
                <Moon size={18} strokeWidth={1.75} aria-hidden />
              ) : (
                <Sun size={18} strokeWidth={1.75} aria-hidden />
              )}
              <span className="settings-menu-row-label">{t.sidebar.menuTheme}</span>
              <span className="settings-menu-row-value">{themeLabel}</span>
              <ChevronRight
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className="settings-menu-chevron"
              />
            </button>
            <button
              type="button"
              role="menuitem"
              className="settings-menu-row"
              onClick={() => setSubview("accent")}
            >
              <Palette size={18} strokeWidth={1.75} aria-hidden />
              <span className="settings-menu-row-label">{t.sidebar.menuAccent}</span>
              <span className="settings-menu-row-value settings-menu-row-value--mono">
                {primarySummary}
              </span>
              <ChevronRight
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className="settings-menu-chevron"
              />
            </button>
            <button
              type="button"
              role="menuitem"
              className="settings-menu-row"
              onClick={() => setSubview("language")}
            >
              <Globe size={18} strokeWidth={1.75} aria-hidden />
              <span className="settings-menu-row-label">
                {t.sidebar.menuLanguage}
              </span>
              <span className="settings-menu-row-value">{langLabel}</span>
              <ChevronRight
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className="settings-menu-chevron"
              />
            </button>
            <div className="settings-menu-divider" role="separator" />
            <button
              type="button"
              role="menuitem"
              className="settings-menu-row"
              onClick={openModel}
            >
              <Monitor size={18} strokeWidth={1.75} aria-hidden />
              <span className="settings-menu-row-label">{t.sidebar.menuModel}</span>
              <ChevronRight
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className="settings-menu-chevron"
              />
            </button>
          </>
        ) : null}

        {subview === "theme" ? (
          <div className="settings-menu-subview">
            <button
              type="button"
              className="settings-menu-back"
              onClick={() => setSubview("main")}
            >
              <ChevronLeft size={18} strokeWidth={1.75} aria-hidden />
              {t.sidebar.subviewBack}
            </button>
            <p className="settings-menu-subtitle">{t.sidebar.menuTheme}</p>
            <div className="settings-menu-options">
              <button
                type="button"
                className={`settings-menu-option${theme === "dark" ? " is-active" : ""}`}
                onClick={() => {
                  setTheme("dark");
                  setSubview("main");
                  setOpen(false);
                }}
              >
                {t.settings.themeDark}
              </button>
              <button
                type="button"
                className={`settings-menu-option${theme === "light" ? " is-active" : ""}`}
                onClick={() => {
                  setTheme("light");
                  setSubview("main");
                  setOpen(false);
                }}
              >
                {t.settings.themeLight}
              </button>
            </div>
          </div>
        ) : null}

        {subview === "accent" ? (
          <div className="settings-menu-subview settings-menu-subview--accent">
            <button
              type="button"
              className="settings-menu-back"
              onClick={() => setSubview("main")}
            >
              <ChevronLeft size={18} strokeWidth={1.75} aria-hidden />
              {t.sidebar.subviewBack}
            </button>
            <p className="settings-menu-subtitle">{t.sidebar.menuAccent}</p>
            <div className="settings-accent-swatches" role="list">
              {PRESET_SWATCHES.map((hex) => {
                const active = hexKeyForCompare(primaryColor) === hexKeyForCompare(hex);
                return (
                  <button
                    key={hex}
                    type="button"
                    role="listitem"
                    className={`settings-accent-swatch${active ? " is-active" : ""}`}
                    style={{ backgroundColor: hex }}
                    onClick={() => setPrimaryColor(hex)}
                    aria-label={hex}
                    aria-pressed={active}
                  >
                    {active ? (
                      <Check
                        size={14}
                        strokeWidth={3}
                        className="settings-accent-swatch-check"
                        aria-hidden
                      />
                    ) : null}
                  </button>
                );
              })}
            </div>
            <p className="settings-accent-custom-label">{t.sidebar.accentCustomColor}</p>
            <div className="settings-accent-picker-row">
              <ColorPicker
                value={primaryColor}
                onChangeComplete={(c) => setPrimaryColor(c.toHexString())}
                format="hex"
                showText
                disabledAlpha={false}
              />
            </div>
          </div>
        ) : null}

        {subview === "language" ? (
          <div className="settings-menu-subview">
            <button
              type="button"
              className="settings-menu-back"
              onClick={() => setSubview("main")}
            >
              <ChevronLeft size={18} strokeWidth={1.75} aria-hidden />
              {t.sidebar.subviewBack}
            </button>
            <p className="settings-menu-subtitle">{t.sidebar.menuLanguage}</p>
            <div className="settings-menu-options">
              <button
                type="button"
                className={`settings-menu-option${locale === "zh" ? " is-active" : ""}`}
                onClick={() => {
                  setLocale("zh");
                  setSubview("main");
                  setOpen(false);
                }}
              >
                {t.settings.languageZh}
              </button>
              <button
                type="button"
                className={`settings-menu-option${locale === "en" ? " is-active" : ""}`}
                onClick={() => {
                  setLocale("en");
                  setSubview("main");
                  setOpen(false);
                }}
              >
                {t.settings.languageEn}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    ) : null;

  return (
    <div className="sidebar-settings-wrap">
      <button
        ref={triggerRef}
        type="button"
        className="sidebar-settings-trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={t.sidebar.settingsButton}
        onClick={() => setOpen((v) => !v)}
      >
        <Settings2 size={18} strokeWidth={1.75} aria-hidden />
        <span>{t.sidebar.settingsButton}</span>
      </button>

      {popoverContent ? createPortal(popoverContent, document.body) : null}

      <ModelSettingsModal
        open={modelOpen}
        onClose={() => setModelOpen(false)}
        triggerRef={triggerRef}
      />
    </div>
  );
}
