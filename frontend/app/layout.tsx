import type { Metadata } from "next";
import Script from "next/script";

import { THEME_STORAGE_KEY } from "../lib/storage-keys";
import "./globals.css";

import { AppProviders } from "./providers";

export const metadata: Metadata = {
  title: "InsightAgent",
  description: "Observable AI Agent frontend shell",
};

const themeInitScript = `
try {
  var t = localStorage.getItem("${THEME_STORAGE_KEY}");
  if (t === "light" || t === "dark") {
    document.documentElement.setAttribute("data-theme", t);
  } else {
    var m = window.matchMedia("(prefers-color-scheme: light)");
    document.documentElement.setAttribute("data-theme", m.matches ? "light" : "dark");
  }
} catch (e) {}
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning data-theme="dark">
      <body suppressHydrationWarning>
        <Script
          id="insightagent-theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: themeInitScript }}
        />
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
