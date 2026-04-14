"use client";

import { ColorPicker } from "antd";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Globe,
  Monitor,
  Moon,
  Palette,
  Settings2,
  ShieldCheck,
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
import { AuditLogsModal } from "./audit-logs-modal";

type SectionId = "theme" | "accent" | "language";

type PopoverPos = { left: number; bottom: number; width: number };

export function SidebarSettingsMenu() {
  const t = useMessages();
  const { theme, setTheme, primaryColor, setPrimaryColor, locale, setLocale } =
    usePreferences();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<SectionId | null>(null);
  const [modelOpen, setModelOpen] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
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
  }, [open, expanded, layoutPopover]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onDocMouseDown(e: MouseEvent) {
      const raw = e.target;
      const target: Element | null =
        raw instanceof Element
          ? raw
          : raw instanceof Node
            ? raw.parentElement
            : null;
      if (!target) return;
      if (triggerRef.current?.contains(target)) return;
      if (popoverRef.current?.contains(target)) return;
      /* ColorPicker 面板默认挂到 body，点击色盘/输入框时不在 popoverRef 内，需排除 */
      if (target.closest("[class*='ant-color-picker']")) return;
      if (target.closest("[class*='rc-color-picker']")) return;
      setOpen(false);
      setExpanded(null);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setExpanded(null);
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
      setExpanded(null);
    }
  }, [open]);

  function toggleSection(id: SectionId) {
    setExpanded((prev) => (prev === id ? null : id));
  }

  function openModel() {
    setOpen(false);
    setExpanded(null);
    setModelOpen(true);
  }

  function openAudit() {
    setOpen(false);
    setExpanded(null);
    setAuditOpen(true);
  }

  const themeLabel =
    theme === "dark" ? t.sidebar.themeCurrentDark : t.sidebar.themeCurrentLight;
  const langLabel =
    locale === "zh" ? t.sidebar.langCurrentZh : t.sidebar.langCurrentEn;

  const primarySummary = primaryColor.toUpperCase();

  const popoverWidth = Math.max(popoverPos?.width ?? 0, 300);

  const popoverContent =
    open && mounted && popoverPos ? (
      <div
        ref={popoverRef}
        className="settings-menu-popover settings-menu-popover--accordion"
        style={{
          position: "fixed",
          left: popoverPos.left,
          bottom: popoverPos.bottom,
          width: popoverWidth,
          zIndex: 450,
        }}
        role="presentation"
      >
        <div className="settings-accordion" role="list" aria-label={t.sidebar.settingsMenuLabel}>
          <div className="settings-accordion-item" role="listitem">
            <button
              type="button"
              className="settings-accordion-trigger"
              aria-expanded={expanded === "theme"}
              aria-controls="settings-section-theme"
              id="settings-heading-theme"
              onClick={() => toggleSection("theme")}
            >
              {theme === "dark" ? (
                <Moon size={18} strokeWidth={1.75} aria-hidden />
              ) : (
                <Sun size={18} strokeWidth={1.75} aria-hidden />
              )}
              <span className="settings-accordion-trigger-label">
                {t.sidebar.menuTheme}
              </span>
              <span className="settings-menu-row-value">{themeLabel}</span>
              <ChevronDown
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className={`settings-accordion-chevron${expanded === "theme" ? " is-expanded" : ""}`}
              />
            </button>
            {expanded === "theme" ? (
              <div
                className="settings-accordion-panel"
                id="settings-section-theme"
                role="region"
                aria-labelledby="settings-heading-theme"
              >
                <div className="settings-menu-options">
                  <button
                    type="button"
                    className={`settings-menu-option${theme === "dark" ? " is-active" : ""}`}
                    onClick={() => setTheme("dark")}
                  >
                    {t.settings.themeDark}
                  </button>
                  <button
                    type="button"
                    className={`settings-menu-option${theme === "light" ? " is-active" : ""}`}
                    onClick={() => setTheme("light")}
                  >
                    {t.settings.themeLight}
                  </button>
                </div>
              </div>
            ) : null}
          </div>

          <div className="settings-accordion-item" role="listitem">
            <button
              type="button"
              className="settings-accordion-trigger"
              aria-expanded={expanded === "accent"}
              aria-controls="settings-section-accent"
              id="settings-heading-accent"
              onClick={() => toggleSection("accent")}
            >
              <Palette size={18} strokeWidth={1.75} aria-hidden />
              <span className="settings-accordion-trigger-label">
                {t.sidebar.menuAccent}
              </span>
              <span className="settings-menu-row-value settings-menu-row-value--mono">
                {primarySummary}
              </span>
              <ChevronDown
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className={`settings-accordion-chevron${expanded === "accent" ? " is-expanded" : ""}`}
              />
            </button>
            {expanded === "accent" ? (
              <div
                className="settings-accordion-panel settings-accordion-panel--accent"
                id="settings-section-accent"
                role="region"
                aria-labelledby="settings-heading-accent"
              >
                <div className="settings-accent-swatches" role="list">
                  {PRESET_SWATCHES.map((hex) => {
                    const active =
                      hexKeyForCompare(primaryColor) === hexKeyForCompare(hex);
                    return (
                      <button
                        key={hex}
                        type="button"
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
                <p className="settings-accent-custom-label">
                  {t.sidebar.accentCustomColor}
                </p>
                <div className="settings-accent-picker-row">
                  <ColorPicker
                    value={primaryColor}
                    onChangeComplete={(c) => setPrimaryColor(c.toHexString())}
                    format="hex"
                    showText
                    disabledAlpha={false}
                    getPopupContainer={() =>
                      popoverRef.current ?? document.body
                    }
                  />
                </div>
              </div>
            ) : null}
          </div>

          <div className="settings-accordion-item" role="listitem">
            <button
              type="button"
              className="settings-accordion-trigger"
              aria-expanded={expanded === "language"}
              aria-controls="settings-section-language"
              id="settings-heading-language"
              onClick={() => toggleSection("language")}
            >
              <Globe size={18} strokeWidth={1.75} aria-hidden />
              <span className="settings-accordion-trigger-label">
                {t.sidebar.menuLanguage}
              </span>
              <span className="settings-menu-row-value">{langLabel}</span>
              <ChevronDown
                size={18}
                strokeWidth={1.75}
                aria-hidden
                className={`settings-accordion-chevron${expanded === "language" ? " is-expanded" : ""}`}
              />
            </button>
            {expanded === "language" ? (
              <div
                className="settings-accordion-panel"
                id="settings-section-language"
                role="region"
                aria-labelledby="settings-heading-language"
              >
                <div className="settings-menu-options">
                  <button
                    type="button"
                    className={`settings-menu-option${locale === "zh" ? " is-active" : ""}`}
                    onClick={() => setLocale("zh")}
                  >
                    {t.settings.languageZh}
                  </button>
                  <button
                    type="button"
                    className={`settings-menu-option${locale === "en" ? " is-active" : ""}`}
                    onClick={() => setLocale("en")}
                  >
                    {t.settings.languageEn}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="settings-menu-divider" role="separator" />

        <button
          type="button"
          role="menuitem"
          className="settings-menu-row settings-menu-row--footer"
          onClick={openAudit}
        >
          <ShieldCheck size={18} strokeWidth={1.75} aria-hidden />
          <span className="settings-menu-row-label">{t.sidebar.menuAudit}</span>
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
          className="settings-menu-row settings-menu-row--footer"
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
      <AuditLogsModal open={auditOpen} onClose={() => setAuditOpen(false)} />
    </div>
  );
}
