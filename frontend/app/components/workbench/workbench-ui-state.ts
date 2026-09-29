export type NarrowDrawers = {
  inspector: boolean;
  session: boolean;
};

export function resolveRemoteSendCooldownUntil(
  mode: string | undefined,
  until: number | null,
): number | null {
  return mode === "remote" ? until : null;
}

export function resolveTaskCenterScope(
  scope: "session" | "global",
  activeSessionId: string | null,
): "session" | "global" {
  return activeSessionId ? scope : "global";
}

export function resolveNarrowDrawers(
  isNarrow: boolean,
  drawers: NarrowDrawers,
): NarrowDrawers {
  if (isNarrow || (!drawers.inspector && !drawers.session)) {
    return drawers;
  }
  return { inspector: false, session: false };
}

export type QueryBannerSource = {
  settingsError: unknown;
  sessionsError: unknown;
  tasksError: unknown;
  messagesError: unknown;
  activeSessionId: string | null;
  errorLabels: unknown;
};

export function reconcileQueryBanner(
  previous: QueryBannerSource,
  source: QueryBannerSource,
  banner: string | null,
  format: (error: unknown) => string,
): { source: QueryBannerSource; banner: string | null } {
  if (
    previous.settingsError === source.settingsError &&
    previous.sessionsError === source.sessionsError &&
    previous.tasksError === source.tasksError &&
    previous.messagesError === source.messagesError &&
    previous.activeSessionId === source.activeSessionId &&
    previous.errorLabels === source.errorLabels
  ) {
    return { source: previous, banner };
  }
  const error =
    source.settingsError ||
    source.sessionsError ||
    source.tasksError ||
    (source.activeSessionId ? source.messagesError : null);
  return { source, banner: banner ?? (error ? format(error) : null) };
}
