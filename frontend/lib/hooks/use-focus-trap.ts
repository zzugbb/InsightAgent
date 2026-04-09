"use client";

import { type RefObject, useEffect } from "react";

/**
 * 抽屉打开时将焦点移入容器，Tab 循环；关闭时恢复到 restoreRef 或先前焦点。
 */
export function useFocusTrap(
  active: boolean,
  containerRef: RefObject<HTMLElement | null>,
  restoreRef?: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!active || !containerRef.current) {
      return;
    }

    const root = containerRef.current;
    const previous = document.activeElement as HTMLElement | null;

    const selector =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function focusable(): HTMLElement[] {
      return Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(
        (el) => !el.hasAttribute("disabled"),
      );
    }

    const nodes = focusable();
    nodes[0]?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Tab") {
        return;
      }
      const list = focusable();
      if (list.length === 0) {
        return;
      }
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    root.addEventListener("keydown", onKeyDown);
    return () => {
      root.removeEventListener("keydown", onKeyDown);
      if (restoreRef?.current) {
        restoreRef.current.focus();
      } else {
        previous?.focus?.();
      }
    };
  }, [active, containerRef, restoreRef]);
}
