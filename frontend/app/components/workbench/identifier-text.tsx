"use client";

import { Typography } from "antd";
import { shortenId } from "./utils";

/** Display a compact reference while copying the complete operational ID. */
export function IdentifierText({ value }: { value: string }) {
  return (
    <Typography.Text
      className="identifier-text"
      title={value}
      copyable={{ text: value }}
    >
      {shortenId(value)}
    </Typography.Text>
  );
}
