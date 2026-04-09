"use client";

import { App, ConfigProvider, theme as antdTheme } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import type { ReactNode } from "react";

import { primaryHexForAntd } from "../lib/theme-primary";
import { usePreferences } from "../lib/preferences-context";

export function AntdThemeProvider({ children }: { children: ReactNode }) {
  const { theme, locale, primaryColor } = usePreferences();
  const { defaultAlgorithm, darkAlgorithm } = antdTheme;
  const algorithm = theme === "dark" ? darkAlgorithm : defaultAlgorithm;
  const primary = primaryHexForAntd(primaryColor);

  return (
    <ConfigProvider
      locale={locale === "zh" ? zhCN : enUS}
      theme={{
        algorithm,
        token: {
          colorPrimary: primary,
          colorLink: primary,
          borderRadiusLG: 14,
          borderRadius: 10,
          borderRadiusSM: 8,
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Noto Sans SC", sans-serif',
          controlHeight: 36,
          controlHeightLG: 40,
        },
        components: {
          Button: { fontWeight: 500, controlOutlineWidth: 0 },
          Input: { activeShadow: "none" },
          Modal: { titleFontSize: 18 },
        },
      }}
    >
      <App>{children}</App>
    </ConfigProvider>
  );
}
