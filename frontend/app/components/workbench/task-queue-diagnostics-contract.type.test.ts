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

const invalidPressureStateDiagnostics: TaskQueueDiagnostics = {
  max_concurrent: 2,
  max_concurrent_per_user: 0,
  max_concurrent_per_session: 0,
  poll_interval_sec: 0.1,
  per_user_limit_enabled: false,
  per_session_limit_enabled: false,
  fairness_limits_enabled: false,
  waiting_policy: "capacity_aware_oldest_eligible_fifo",
  capacity_aware_fifo_enabled: true,
  // @ts-expect-error pressure_state is a fixed backend diagnostics enum.
  pressure_state: "waiting",
};

const invalidWaitingPolicyDiagnostics: TaskQueueDiagnostics = {
  max_concurrent: 2,
  max_concurrent_per_user: 0,
  max_concurrent_per_session: 0,
  poll_interval_sec: 0.1,
  per_user_limit_enabled: false,
  per_session_limit_enabled: false,
  fairness_limits_enabled: false,
  // @ts-expect-error waiting_policy is a fixed backend diagnostics policy id.
  waiting_policy: "plain_fifo",
  capacity_aware_fifo_enabled: true,
};

void invalidPressureStateDiagnostics;
void invalidWaitingPolicyDiagnostics;
