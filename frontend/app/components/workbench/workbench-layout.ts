export const SIDEBAR_W_MIN = 200;
export const SIDEBAR_W_MAX = 480;
export const INSPECTOR_W_MIN = 260;
export const INSPECTOR_W_MAX = 560;

export type WorkbenchLayout = {
  sidebarWidthPx: number;
  sidebarCollapsed: boolean;
  inspectorWidthPx: number;
  inspectorCollapsed: boolean;
};

export type WorkbenchLayoutStorageKeys = {
  sidebarWidth: string;
  sidebarCollapsed: string;
  inspectorWidth: string;
  inspectorCollapsed: string;
};

export const DEFAULT_WORKBENCH_LAYOUT: WorkbenchLayout = {
  sidebarWidthPx: 280,
  sidebarCollapsed: false,
  inspectorWidthPx: 340,
  inspectorCollapsed: false,
};

function readWidth(raw: string | null, fallback: number, min: number, max: number) {
  if (!raw) return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? fallback : Math.min(max, Math.max(min, parsed));
}

export function readStoredWorkbenchLayout(
  storage: { getItem: (key: string) => string | null } | null,
  keys: WorkbenchLayoutStorageKeys,
): WorkbenchLayout {
  if (!storage) return DEFAULT_WORKBENCH_LAYOUT;
  try {
    return {
      sidebarWidthPx: readWidth(storage.getItem(keys.sidebarWidth), 280, SIDEBAR_W_MIN, SIDEBAR_W_MAX),
      sidebarCollapsed: storage.getItem(keys.sidebarCollapsed) === "1",
      inspectorWidthPx: readWidth(storage.getItem(keys.inspectorWidth), 340, INSPECTOR_W_MIN, INSPECTOR_W_MAX),
      inspectorCollapsed: storage.getItem(keys.inspectorCollapsed) === "1",
    };
  } catch {
    return DEFAULT_WORKBENCH_LAYOUT;
  }
}

export function selectHydratedWorkbenchLayout(
  stored: WorkbenchLayout,
  hydrated: boolean,
): WorkbenchLayout {
  return hydrated ? stored : DEFAULT_WORKBENCH_LAYOUT;
}
