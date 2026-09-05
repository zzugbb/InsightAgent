import { Alert, Button } from "antd";
import { RefreshCw } from "lucide-react";

import type { UserFacingError } from "../../../lib/errors";

type RuntimeDebugRecoveryAlertProps = {
  title: string;
  error: UserFacingError;
  guidance: string;
  retryLabel: string;
  canRetry: boolean;
  retrying: boolean;
  onRetry: () => void;
  testId: string;
};

export function RuntimeDebugRecoveryAlert({
  title,
  error,
  guidance,
  retryLabel,
  canRetry,
  retrying,
  onRetry,
  testId,
}: RuntimeDebugRecoveryAlertProps) {
  const errorText = error.hint
    ? `${error.banner} ${error.hint}`
    : error.banner;

  return (
    <Alert
      type="error"
      showIcon
      data-testid={testId}
      title={title}
      description={
        <div>
          <div>{errorText}</div>
          <div>{guidance}</div>
        </div>
      }
      action={
        canRetry ? (
          <Button
            size="small"
            icon={<RefreshCw size={14} aria-hidden />}
            loading={retrying}
            data-testid={`${testId}-retry`}
            onClick={onRetry}
          >
            {retryLabel}
          </Button>
        ) : undefined
      }
    />
  );
}
