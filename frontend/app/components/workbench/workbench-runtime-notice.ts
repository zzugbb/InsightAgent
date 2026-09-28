export type RuntimeNoticeSource = {
  mode: string | undefined;
  apiKeyConfigured: boolean | undefined;
};

export type RuntimeNoticeDismissal = RuntimeNoticeSource & {
  dismissed: boolean;
};

export function reconcileRuntimeNoticeDismissal(
  state: RuntimeNoticeDismissal,
  source: RuntimeNoticeSource,
): RuntimeNoticeDismissal {
  if (
    state.mode === source.mode &&
    state.apiKeyConfigured === source.apiKeyConfigured
  ) {
    return state;
  }
  return { ...source, dismissed: false };
}
