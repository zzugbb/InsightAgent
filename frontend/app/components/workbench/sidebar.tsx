"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { Trash2 } from "lucide-react";
import { forwardRef, useRef } from "react";

import { useMessages, usePreferences } from "../../../lib/preferences-context";

import { SidebarSettingsMenu } from "./sidebar-settings-menu";
import type { SessionSummary } from "./types";
import { formatTimestamp, getSessionLabel } from "./utils";

const VIRTUAL_THRESHOLD = 14;

type SidebarProps = {
  recentSessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  deletingSessionId: string | null;
  sessionsLoading: boolean;
  sessionsMessage: string;
  onNewSession: () => void;
  newSessionBusy: boolean;
  drawerMode: boolean;
};

export const Sidebar = forwardRef<HTMLElement, SidebarProps>(function Sidebar(
  {
    recentSessions,
    activeSessionId,
    onSelectSession,
    onDeleteSession,
    deletingSessionId,
    sessionsLoading,
    sessionsMessage,
    onNewSession,
    newSessionBusy,
    drawerMode,
  },
  ref,
) {
  const t = useMessages();
  const { localeTag } = usePreferences();
  const listParentRef = useRef<HTMLDivElement>(null);

  const useVirtual = recentSessions.length > VIRTUAL_THRESHOLD && !sessionsLoading;

  const virtualizer = useVirtualizer({
    count: recentSessions.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => 84,
    overscan: 6,
    enabled: useVirtual,
  });

  return (
    <aside
      ref={ref}
      className={`app-sidebar${drawerMode ? " app-sidebar--drawer" : ""}`}
      aria-label={t.sidebar.ariaLabel}
    >
      <div className="brand-block">
        <p className="brand-kicker">InsightAgent</p>
        <h1>{t.sidebar.brandTitle}</h1>
        <p>{t.sidebar.brandLead}</p>
      </div>

      <div className="sidebar-section sidebar-section-grow">
        <div className="sidebar-section-head">
          <div className="sidebar-section-title-row">
            <h2 id="sessions-heading">{t.sidebar.sessionsHeading}</h2>
            <button
              type="button"
              className="ghost-button sidebar-new-session"
              onClick={onNewSession}
              disabled={newSessionBusy || sessionsLoading}
            >
              {newSessionBusy ? t.sidebar.creating : t.sidebar.newSession}
            </button>
          </div>
          <span className={sessionsLoading ? "text-muted-loading" : ""}>
            {sessionsLoading ? t.sidebar.loading : sessionsMessage}
          </span>
        </div>
        <div
          ref={listParentRef}
          className="sidebar-list"
          aria-labelledby="sessions-heading"
        >
          {sessionsLoading && recentSessions.length === 0 ? (
            <>
              <div className="skeleton sidebar-skeleton-item" />
              <div className="skeleton sidebar-skeleton-item" />
              <div className="skeleton sidebar-skeleton-item" />
            </>
          ) : recentSessions.length > 0 ? (
            useVirtual ? (
              <div
                className="sidebar-virtual-inner"
                style={{ height: virtualizer.getTotalSize(), position: "relative" }}
              >
                {virtualizer.getVirtualItems().map((vi) => {
                  const session = recentSessions[vi.index];
                  const isActive = session.id === activeSessionId;
                  const deleting = deletingSessionId === session.id;
                  return (
                    <div
                      key={session.id}
                      className="sidebar-virtual-row"
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        transform: `translateY(${vi.start}px)`,
                      }}
                    >
                      <div
                        className={`sidebar-session-row${isActive ? " is-active" : ""}`}
                      >
                        <button
                          className="sidebar-item"
                          type="button"
                          aria-current={isActive ? "true" : undefined}
                          onClick={() => onSelectSession(session.id)}
                        >
                          <strong>{getSessionLabel(session, t.workbench)}</strong>
                          <span>{formatTimestamp(session.updated_at, localeTag)}</span>
                        </button>
                        <button
                          type="button"
                          className="sidebar-session-delete"
                          aria-label={t.sidebar.deleteSessionAria}
                          disabled={deleting || sessionsLoading}
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.id);
                          }}
                        >
                          <Trash2 size={18} strokeWidth={2} aria-hidden />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              recentSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                const deleting = deletingSessionId === session.id;
                return (
                  <div
                    key={session.id}
                    className={`sidebar-session-row${isActive ? " is-active" : ""}`}
                  >
                    <button
                      className="sidebar-item"
                      type="button"
                      aria-current={isActive ? "true" : undefined}
                      onClick={() => onSelectSession(session.id)}
                    >
                      <strong>{getSessionLabel(session, t.workbench)}</strong>
                      <span>{formatTimestamp(session.updated_at, localeTag)}</span>
                    </button>
                    <button
                      type="button"
                      className="sidebar-session-delete"
                      aria-label={t.sidebar.deleteSessionAria}
                      disabled={deleting || sessionsLoading}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                    >
                      <Trash2 size={18} strokeWidth={2} aria-hidden />
                    </button>
                  </div>
                );
              })
            )
          ) : (
            <div className="sidebar-empty">{t.sidebar.empty}</div>
          )}
        </div>
      </div>

      <div className="sidebar-footer">
        <SidebarSettingsMenu />
      </div>
    </aside>
  );
});
