import type { TaskQueueDiagnostics } from "./types";

// @ts-expect-error queue diagnostics governance fields are required by backend e2e helpers.
const missingGovernanceDiagnostics: TaskQueueDiagnostics = {
  max_concurrent: 2,
  max_concurrent_per_user: 0,
  max_concurrent_per_session: 0,
  poll_interval_sec: 0.1,
  per_user_limit_enabled: false,
  per_session_limit_enabled: false,
  fairness_limits_enabled: false,
};

void missingGovernanceDiagnostics;
