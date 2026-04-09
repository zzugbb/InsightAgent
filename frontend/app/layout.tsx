import type { Metadata } from "next";
import Script from "next/script";

import { AntdRegistry } from "@ant-design/nextjs-registry";

import {
  PRIMARY_COLOR_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "../lib/storage-keys";
import "./globals.css";

import { AppProviders } from "./providers";

export const metadata: Metadata = {
  title: "InsightAgent",
  description: "可观测智能体工作台：对话为主，执行过程在右侧轨迹中展开。",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32", type: "image/x-icon" },
    ],
  },
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
  var pk = "${PRIMARY_COLOR_STORAGE_KEY}";
  var hex = localStorage.getItem(pk);
  var hexOk = /^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/.test(hex || "");
  if (!hexOk) {
    var leg = localStorage.getItem("insightagent.accent");
    var map = { emerald: "#22c55e", sky: "#0ea5e9", violet: "#a78bfa", amber: "#f59e0b", rose: "#fb7185" };
    hex = (leg && map[leg]) || "#22c55e";
  }
  document.documentElement.style.setProperty("--accent", hex);
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
        <AntdRegistry>
          <AppProviders>{children}</AppProviders>
        </AntdRegistry>
      </body>
    </html>
  );
}
