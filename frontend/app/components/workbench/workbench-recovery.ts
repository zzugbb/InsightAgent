export type RecoveryPreparation = {
  preparedTaskIds: string[];
  launchTaskId: string | null;
};

export function reconcileRecoveryPreparation(
  previous: RecoveryPreparation,
  runningTaskIds: readonly string[],
  candidateId: string | null,
): RecoveryPreparation {
  const running = new Set(runningTaskIds);
  const preparedTaskIds = previous.preparedTaskIds.filter((id) => running.has(id));
  let launchTaskId = previous.launchTaskId && running.has(previous.launchTaskId)
    ? previous.launchTaskId
    : null;
  if (candidateId && running.has(candidateId) && !preparedTaskIds.includes(candidateId)) {
    preparedTaskIds.push(candidateId);
    launchTaskId = candidateId;
  }
  if (
    launchTaskId === previous.launchTaskId &&
    preparedTaskIds.length === previous.preparedTaskIds.length
  ) {
    return previous;
  }
  return { preparedTaskIds, launchTaskId };
}
