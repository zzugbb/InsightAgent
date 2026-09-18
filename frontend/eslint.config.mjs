import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const setStateInEffectMigrationFiles = [
  "app/components/workbench/index.tsx",
  "app/components/workbench/knowledge-base-governance-modal.tsx",
  "app/components/workbench/model-settings-modal.tsx",
  "app/components/workbench/runtime-debug-modal.tsx",
  "app/components/workbench/sidebar-settings-menu.tsx",
  "app/components/workbench/task-center.tsx",
  "app/components/workbench/usage-dashboard-modal.tsx",
  "lib/preferences-context.tsx",
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: setStateInEffectMigrationFiles,
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
