"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import type { Pluggable } from "unified";
import "katex/dist/katex.min.css";

import { markdownSanitizeSchema } from "../../../lib/markdown-sanitize-schema";

const markdownComponents: Components = {
  a: ({ href, children, ...rest }) => (
    <a
      {...rest}
      href={href}
      className="markdown-link"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
};

const rehypePlugins: Pluggable[] = [
  rehypeHighlight,
  [
    rehypeKatex,
    { strict: false, throwOnError: false, errorColor: "var(--danger)" },
  ],
  [rehypeSanitize, markdownSanitizeSchema],
];

type MessageBodyProps = {
  text: string;
};

/** GFM + 数学公式 + 代码高亮 + 安全消毒；外链新标签打开。 */
export function MessageBody({ text }: MessageBodyProps) {
  if (!text.trim()) {
    return null;
  }

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={rehypePlugins}
        components={markdownComponents}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
