import {
  ACCENT_STORAGE_KEY,
  PRIMARY_COLOR_STORAGE_KEY,
} from "./storage-keys";

/** 默认主题色（原翠绿） */
export const DEFAULT_PRIMARY_HEX = "#22c55e";

export { PRIMARY_COLOR_STORAGE_KEY };

const HEX_RE = /^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;

/** 快捷色块（参考常见主题色板） */
export const PRESET_SWATCHES = [
  "#2563eb",
  "#dc2626",
  "#ea580c",
  "#ca8a04",
  "#0891b2",
  "#16a34a",
  "#0f766e",
  "#9333ea",
] as const;

const LEGACY_ACCENT_TO_HEX: Record<string, string> = {
  emerald: "#22c55e",
  sky: "#0ea5e9",
  violet: "#a78bfa",
  amber: "#f59e0b",
  rose: "#fb7185",
};

export function normalizePrimaryHex(input: string): string | null {
  const t = input.trim();
  if (!HEX_RE.test(t)) return null;
  return t;
}

/** 用于比较预设选中：统一为 #rrggbb 小写 */
export function hexKeyForCompare(hex: string): string {
  const n = normalizePrimaryHex(hex);
  if (!n) return "";
  return n.slice(0, 7).toLowerCase();
}

/** 供 Ant Design token（仅 6 位 hex） */
export function primaryHexForAntd(stored: string): string {
  const n = normalizePrimaryHex(stored);
  if (!n) return DEFAULT_PRIMARY_HEX;
  return n.slice(0, 7);
}

export function readStoredPrimaryColor(): string {
  if (typeof window === "undefined") return DEFAULT_PRIMARY_HEX;

  const raw = localStorage.getItem(PRIMARY_COLOR_STORAGE_KEY);
  const direct = raw && normalizePrimaryHex(raw);
  if (direct) return direct;

  const legacy = localStorage.getItem(ACCENT_STORAGE_KEY);
  if (legacy && LEGACY_ACCENT_TO_HEX[legacy]) {
    return LEGACY_ACCENT_TO_HEX[legacy];
  }

  return DEFAULT_PRIMARY_HEX;
}

export function applyPrimaryColorToDocument(cssColor: string): void {
  if (typeof document === "undefined") return;
  document.documentElement.style.setProperty("--accent", cssColor);
}
