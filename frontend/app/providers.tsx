"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { AntdThemeProvider } from "./antd-theme-provider";
import { PreferencesProvider } from "../lib/preferences-context";

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 8_000,
            refetchOnWindowFocus: true,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <PreferencesProvider>
        <AntdThemeProvider>{children}</AntdThemeProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
