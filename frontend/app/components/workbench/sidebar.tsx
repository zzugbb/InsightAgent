"use client";

import { Button, Dropdown, Input, Modal, type MenuProps } from "antd";
import { useVirtualizer } from "@tanstack/react-virtual";
import { MoreHorizontal, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { forwardRef, useCallback, useRef, useState } from "react";

import { useMessages } from "../../../lib/preferences-context";

import { BrandLogo } from "./brand-logo";
import { SidebarSettingsMenu } from "./sidebar-settings-menu";
import type { SessionSummary } from "./types";
import { getSessionLabel } from "./utils";

const VIRTUAL_THRESHOLD = 14;

type SidebarProps = {
  recentSessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => Promise<unknown>;
  deletingSessionId: string | null;
  renamingSessionId: string | null;
  sessionsLoading: boolean;
  sessionsMessage: string;
  onNewSession: () => void;
  newSessionBusy: boolean;
  drawerMode: boolean;
  desktopSidebarChrome: boolean;
  sidebarCollapsed: boolean;
  onToggleSidebarCollapsed: () => void;
  onSidebarResizeStart: (event: React.MouseEvent) => void;
};

export const Sidebar = forwardRef<HTMLElement, SidebarProps>(function Sidebar(
  {
    recentSessions,
    activeSessionId,
    onSelectSession,
    onDeleteSession,
    onRenameSession,
    deletingSessionId,
    renamingSessionId,
    sessionsLoading,
    sessionsMessage,
    onNewSession,
    newSessionBusy,
    drawerMode,
    desktopSidebarChrome,
    sidebarCollapsed,
    onToggleSidebarCollapsed,
    onSidebarResizeStart,
  },
  ref,
) {
  const t = useMessages();
  const listParentRef = useRef<HTMLDivElement>(null);

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<SessionSummary | null>(null);
  const [renameDraft, setRenameDraft] = useState("");

  const useVirtual =
    recentSessions.length > VIRTUAL_THRESHOLD && !sessionsLoading;

  const virtualizer = useVirtualizer({
    count: recentSessions.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => 40,
    overscan: 6,
    enabled: useVirtual,
  });

  const openRename = useCallback((session: SessionSummary) => {
    setRenameTarget(session);
    setRenameDraft(getSessionLabel(session, t.workbench));
    setRenameOpen(true);
  }, [t.workbench]);

  const submitRename = useCallback(async () => {
    if (!renameTarget) return;
    const title = renameDraft.trim() || "新会话";
    await onRenameSession(renameTarget.id, title);
    setRenameOpen(false);
    setRenameTarget(null);
  }, [renameDraft, renameTarget, onRenameSession]);

  const buildMenuItems = useCallback(
    (session: SessionSummary): MenuProps["items"] => [
      {
        key: "rename",
        label: t.sidebar.renameSessionMenu,
        onClick: ({ domEvent }) => {
          domEvent.stopPropagation();
          openRename(session);
        },
      },
      {
        type: "divider",
      },
      {
        key: "delete",
        label: t.sidebar.deleteSessionMenu,
        danger: true,
        onClick: ({ domEvent }) => {
          domEvent.stopPropagation();
          onDeleteSession(session.id);
        },
      },
    ],
    [onDeleteSession, openRename, t.sidebar],
  );

  function renderSessionRow(session: SessionSummary) {
    const isActive = session.id === activeSessionId;
    const deleting = deletingSessionId === session.id;
    return (
      <div
        key={session.id}
        className={`sidebar-session-row${isActive ? " is-active" : ""}`}
      >
        <button
          className="sidebar-item sidebar-item--single"
          type="button"
          aria-current={isActive ? "true" : undefined}
          disabled={sessionsLoading}
          onClick={() => onSelectSession(session.id)}
        >
          <span className="sidebar-item-title">
            {getSessionLabel(session, t.workbench)}
          </span>
        </button>
        <Dropdown
          menu={{ items: buildMenuItems(session) }}
          trigger={["click"]}
          placement="bottomRight"
        >
          <Button
            type="text"
            size="small"
            className="sidebar-session-more"
            aria-label={t.sidebar.sessionMoreAria}
            disabled={sessionsLoading || deleting}
            loading={deleting}
            icon={<MoreHorizontal size={18} strokeWidth={2} aria-hidden />}
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>
      </div>
    );
  }

  const collapsedRail = desktopSidebarChrome && sidebarCollapsed;

  return (
    <aside
      ref={ref}
      className={`app-sidebar${drawerMode ? " app-sidebar--drawer" : ""}${collapsedRail ? " app-sidebar--collapsed" : ""}`}
      aria-label={t.sidebar.ariaLabel}
    >
      {desktopSidebarChrome && !sidebarCollapsed ? (
        <div
          className="sidebar-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-hidden
          onMouseDown={onSidebarResizeStart}
        />
      ) : null}

      {collapsedRail ? (
        <div className="sidebar-collapsed-inner">
          <div className="sidebar-collapsed-logo" title="InsightAgent">
            <BrandLogo className="brand-logo-mark" size={28} />
          </div>
          <Button
            type="text"
            className="sidebar-expand-btn"
            aria-label={t.sidebar.expandSidebarAria}
            title={t.sidebar.expandSidebarAria}
            icon={<PanelLeftOpen size={20} strokeWidth={2} aria-hidden />}
            onClick={onToggleSidebarCollapsed}
          />
        </div>
      ) : (
        <>
          <div className="brand-block">
            <div className="brand-block-head">
              <div className="brand-block-identity">
                <BrandLogo className="brand-logo-mark" size={36} />
                <div className="brand-copy">
                  <div className="brand-wordmark" translate="no">
                    <span className="brand-product">InsightAgent</span>
                  </div>
                  <p className="brand-tagline">{t.sidebar.brandTitle}</p>
                  <p className="brand-lead">{t.sidebar.brandLead}</p>
                </div>
              </div>
              {desktopSidebarChrome ? (
                <Button
                  type="text"
                  size="small"
                  className="sidebar-collapse-btn brand-collapse-btn"
                  aria-label={t.sidebar.collapseSidebarAria}
                  title={t.sidebar.collapseSidebarAria}
                  icon={
                    <PanelLeftClose size={18} strokeWidth={2} aria-hidden />
                  }
                  onClick={onToggleSidebarCollapsed}
                />
              ) : null}
            </div>
          </div>

          <div className="sidebar-section sidebar-section-grow">
            <div className="sidebar-section-head">
              <div className="sidebar-section-title-row">
                <h2 id="sessions-heading">{t.sidebar.sessionsHeading}</h2>
                <div className="sidebar-head-actions">
                  <Button
                    type="primary"
                    ghost
                    className="sidebar-new-session"
                    onClick={onNewSession}
                    disabled={sessionsLoading}
                    loading={newSessionBusy}
                  >
                    {newSessionBusy ? t.sidebar.creating : t.sidebar.newSession}
                  </Button>
                </div>
              </div>
              {sessionsLoading || sessionsMessage ? (
                <span className={sessionsLoading ? "text-muted-loading" : ""}>
                  {sessionsLoading ? t.sidebar.loading : sessionsMessage}
                </span>
              ) : null}
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
                    style={{
                      height: virtualizer.getTotalSize(),
                      position: "relative",
                    }}
                  >
                    {virtualizer.getVirtualItems().map((vi) => {
                      const session = recentSessions[vi.index];
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
                          {renderSessionRow(session)}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  recentSessions.map((session) => renderSessionRow(session))
                )
              ) : (
                <div className="sidebar-empty">{t.sidebar.empty}</div>
              )}
            </div>
          </div>

          <div className="sidebar-footer">
            <SidebarSettingsMenu />
          </div>
        </>
      )}

      <Modal
        title={t.sidebar.renameSessionModalTitle}
        open={renameOpen}
        okText={t.sidebar.renameSessionSave}
        confirmLoading={Boolean(renamingSessionId)}
        onOk={() => void submitRename()}
        onCancel={() => {
          setRenameOpen(false);
          setRenameTarget(null);
        }}
        destroyOnHidden
      >
        <Input
          value={renameDraft}
          placeholder={t.sidebar.renameSessionPlaceholder}
          maxLength={120}
          onChange={(e) => setRenameDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              void submitRename();
            }
          }}
        />
      </Modal>
    </aside>
  );
});
