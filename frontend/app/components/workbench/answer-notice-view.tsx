"use client";

import { Alert } from "antd";
import { useMessages } from "../../../lib/preferences-context";
import type { AnswerNoticeCode } from "./answer-notices";

export function AnswerNoticeView({ codes }: { codes: AnswerNoticeCode[] }) {
  const t = useMessages();
  if (!codes.length) return null;
  return (
    <div data-testid="answer-notices">
      {codes.map((code) => <Alert key={code} type="warning" showIcon
        description={t.chat.answerNotices[code]} />)}
    </div>
  );
}
