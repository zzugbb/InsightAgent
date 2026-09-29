import { useEffect, useState, useSyncExternalStore } from "react";

import {
  INSPECTOR_COLLAPSED_STORAGE_KEY,
  INSPECTOR_WIDTH_STORAGE_KEY,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../../../lib/storage-keys";
import {
  readStoredWorkbenchLayout,
  selectHydratedWorkbenchLayout,
} from "./workbench-layout";

const storageKeys = {
  sidebarWidth: SIDEBAR_WIDTH_STORAGE_KEY,
  sidebarCollapsed: SIDEBAR_COLLAPSED_STORAGE_KEY,
  inspectorWidth: INSPECTOR_WIDTH_STORAGE_KEY,
  inspectorCollapsed: INSPECTOR_COLLAPSED_STORAGE_KEY,
};

function subscribeToHydration() {
  return () => {};
}

function getClientHydrationSnapshot() {
  return true;
}

function getServerHydrationSnapshot() {
  return false;
}

export function useWorkbenchLayout() {
  const hydrated = useSyncExternalStore(
    subscribeToHydration,
    getClientHydrationSnapshot,
    getServerHydrationSnapshot,
  );
  const [initialLayout] = useState(() =>
    readStoredWorkbenchLayout(
      typeof localStorage === "undefined" ? null : localStorage,
      storageKeys,
    ),
  );
  const [sidebarWidthPx, setSidebarWidthPx] = useState(initialLayout.sidebarWidthPx);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(initialLayout.sidebarCollapsed);
  const [inspectorWidthPx, setInspectorWidthPx] = useState(initialLayout.inspectorWidthPx);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(initialLayout.inspectorCollapsed);
  const layout = selectHydratedWorkbenchLayout(
    { sidebarWidthPx, sidebarCollapsed, inspectorWidthPx, inspectorCollapsed },
    hydrated,
  );

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(storageKeys.sidebarWidth, String(sidebarWidthPx));
      localStorage.setItem(storageKeys.sidebarCollapsed, sidebarCollapsed ? "1" : "0");
      localStorage.setItem(storageKeys.inspectorWidth, String(inspectorWidthPx));
      localStorage.setItem(storageKeys.inspectorCollapsed, inspectorCollapsed ? "1" : "0");
    } catch {
      // Browsers can deny local storage; the in-memory layout remains usable.
    }
  }, [hydrated, sidebarWidthPx, sidebarCollapsed, inspectorWidthPx, inspectorCollapsed]);

  return {
    ...layout,
    setSidebarWidthPx,
    setSidebarCollapsed,
    setInspectorWidthPx,
    setInspectorCollapsed,
  };
}
