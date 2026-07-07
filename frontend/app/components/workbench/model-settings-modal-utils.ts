import type {
  SettingsSummary,
  ToolRegistryDiagnosticsSummary,
  SettingsValidateResponse,
  ToolRegistryProviderSourceOptionDetail,
  ToolRegistryProviderToolDetail,
} from "./types";

type ModelSettingsPreviewSource = Pick<
  SettingsSummary,
  | "enabled_tool_labels"
  | "available_tool_registry_profile_details"
  | "available_tool_registry_provider_source_details"
> &
  Pick<
    SettingsValidateResponse,
    | "enabled_tool_labels"
    | "available_tool_registry_profile_details"
    | "available_tool_registry_provider_source_details"
  >;

function formatToolSemanticDescriptor(
  tool: Pick<
    ToolRegistryProviderToolDetail,
    "kind" | "semantic_kind" | "semantic_family" | "execution_kind"
  >,
): string {
  const semanticKind =
    typeof tool.semantic_kind === "string" && tool.semantic_kind.trim().length > 0
      ? tool.semantic_kind.trim()
      : tool.kind;
  const semanticFamily =
    typeof tool.semantic_family === "string" && tool.semantic_family.trim().length > 0
      ? tool.semantic_family.trim()
      : "";
  if (!semanticFamily || semanticFamily === semanticKind) {
    const executionKind =
      typeof tool.execution_kind === "string" && tool.execution_kind.trim().length > 0
        ? tool.execution_kind.trim()
        : "";
    return executionKind ? `${semanticKind} via ${executionKind}` : semanticKind;
  }
  const baseDescriptor = `${semanticKind} · ${semanticFamily}`;
  const executionKind =
    typeof tool.execution_kind === "string" && tool.execution_kind.trim().length > 0
      ? tool.execution_kind.trim()
      : "";
  return executionKind ? `${baseDescriptor} via ${executionKind}` : baseDescriptor;
}

function formatToolExecutionSummary(
  tool: Pick<ToolRegistryProviderToolDetail, "execution_summary">,
): string {
  const executionSummary = tool.execution_summary;
  if (!executionSummary) {
    return "";
  }
  const method =
    typeof executionSummary.method === "string" && executionSummary.method.trim().length > 0
      ? executionSummary.method.trim().toUpperCase()
      : "";
  const urlOrigin =
    typeof executionSummary.url_origin === "string" && executionSummary.url_origin.trim().length > 0
      ? executionSummary.url_origin.trim()
      : "";
  const urlPath =
    typeof executionSummary.url_path === "string" && executionSummary.url_path.trim().length > 0
      ? executionSummary.url_path.trim()
      : "";
  const endpoint = `${urlOrigin}${urlPath}`;
  if (!method && !endpoint) {
    return "";
  }
  const parts = [[method, endpoint].filter((part) => part.length > 0).join(" ")];
  const headerCount = executionSummary.header_count;
  if (typeof headerCount === "number" && Number.isFinite(headerCount) && headerCount > 0) {
    parts.push(`headers ${Math.trunc(headerCount)}`);
  }
  const queryParamCount = executionSummary.query_param_count;
  if (
    typeof queryParamCount === "number"
    && Number.isFinite(queryParamCount)
    && queryParamCount > 0
  ) {
    parts.push(`query ${Math.trunc(queryParamCount)}`);
  }
  const jsonBodyFieldCount = executionSummary.json_body_field_count;
  if (
    typeof jsonBodyFieldCount === "number"
    && Number.isFinite(jsonBodyFieldCount)
    && jsonBodyFieldCount > 0
  ) {
    parts.push(`body ${Math.trunc(jsonBodyFieldCount)}`);
  }
  const responsePath =
    typeof executionSummary.response_path === "string" && executionSummary.response_path.trim().length > 0
      ? executionSummary.response_path.trim()
      : "";
  if (responsePath) {
    parts.push(`response ${responsePath}`);
  }
  const resultFieldNames = Array.isArray(executionSummary.result_field_names)
    ? executionSummary.result_field_names.filter((name) => name.trim().length > 0)
    : [];
  if (resultFieldNames.length > 0) {
    parts.push(`fields ${resultFieldNames.join(", ")}`);
  }
  return parts.filter((part) => part.length > 0).join(" · ");
}

function formatToolExecutionDiagnostics(
  tool: Pick<ToolRegistryProviderToolDetail, "execution_diagnostics">,
): string {
  const executionDiagnostics = Array.isArray(tool.execution_diagnostics)
    ? tool.execution_diagnostics.filter((value) => value.trim().length > 0)
    : [];
  if (executionDiagnostics.length === 0) {
    return "";
  }
  return executionDiagnostics.join(", ");
}

export function formatToolRegistryProviderToolDetailsSummary(
  toolDetails: ToolRegistryProviderToolDetail[] | undefined,
): string {
  if (!toolDetails || toolDetails.length === 0) {
    return "—";
  }
  return toolDetails
    .map((tool) => {
      const semanticDescriptor = formatToolSemanticDescriptor(tool);
      const executionSummary = formatToolExecutionSummary(tool);
      const semanticOrKind = executionSummary
        ? `${semanticDescriptor} @ ${executionSummary}`
        : semanticDescriptor;
      const executionDiagnostics = formatToolExecutionDiagnostics(tool);
      const previewKeys =
        Array.isArray(tool.effective_result_preview_keys)
          ? tool.effective_result_preview_keys.filter((key) => key.trim().length > 0)
          : [];
      const outputKeys =
        Array.isArray(tool.effective_result_output_keys)
          ? tool.effective_result_output_keys.filter((key) => key.trim().length > 0)
          : [];
      const suffixes: string[] = [];
      if (previewKeys.length > 0 && outputKeys.length > 0) {
        suffixes.push(`preview ${previewKeys.join(", ")}`);
        suffixes.push(`output ${outputKeys.join(", ")}`);
      } else if (previewKeys.length > 0) {
        suffixes.push(previewKeys.join(", "));
      } else if (outputKeys.length > 0) {
        suffixes.push(`output ${outputKeys.join(", ")}`);
      }
      if (executionDiagnostics) {
        suffixes.push(`diagnostics ${executionDiagnostics}`);
      }
      if (suffixes.length === 0) {
        return `${tool.label} [${semanticOrKind}]`;
      }
      return `${tool.label} [${semanticOrKind}]: ${suffixes.join("; ")}`;
    })
    .join(" | ");
}

function humanizeDiagnosticsTarget(target: string): string {
  const normalized = target.trim().toLowerCase();
  if (!normalized) {
    return "diagnostics";
  }
  return normalized.replaceAll("_", " ");
}

export function formatToolRegistryProviderSourceDiagnosticsSummary(
  diagnosticsSummary: ToolRegistryDiagnosticsSummary | undefined,
): string {
  if (!diagnosticsSummary?.has_diagnostics || diagnosticsSummary.entries.length === 0) {
    return "—";
  }
  return diagnosticsSummary.entries
    .map((entry) => {
      const label = `${entry.kind} ${humanizeDiagnosticsTarget(entry.target)}`.trim();
      const values = Array.isArray(entry.values)
        ? entry.values.filter((value) => value.trim().length > 0)
        : [];
      if (values.length === 0) {
        return `${label}: ${entry.count}`;
      }
      return `${label}: ${values.join(", ")}`;
    })
    .join(" | ");
}

function findSelectedSourceDetail(
  previewSource: ModelSettingsPreviewSource | null,
  sourceName: string,
): ToolRegistryProviderSourceOptionDetail | null {
  if (!previewSource?.available_tool_registry_provider_source_details) {
    return null;
  }
  return (
    previewSource.available_tool_registry_provider_source_details.find(
      (detail) => detail.name === sourceName,
    ) ?? null
  );
}

export function resolveModelSettingsSelectionDetails(args: {
  previewSource: ModelSettingsPreviewSource | null;
  profileName: string;
  sourceName: string;
}): {
  selectedProfileTools: string;
  selectedProfileToolDetailsSummary: string;
  selectedSourceTools: string;
  selectedSourceBaseProfile: string;
  selectedSourceDiagnosticsSummary: string;
  selectedSourceToolDetailsSummary: string;
} {
  const selectedProfileDetail =
    args.previewSource?.available_tool_registry_profile_details?.find(
      (detail) => detail.name === args.profileName,
    ) ?? null;
  const selectedSourceDetail = findSelectedSourceDetail(
    args.previewSource,
    args.sourceName,
  );
  return {
    selectedProfileTools:
      selectedProfileDetail && selectedProfileDetail.enabled_tool_labels.length > 0
        ? selectedProfileDetail.enabled_tool_labels.join(", ")
        : "—",
    selectedProfileToolDetailsSummary: formatToolRegistryProviderToolDetailsSummary(
      selectedProfileDetail?.tool_details,
    ),
    selectedSourceTools:
      selectedSourceDetail && selectedSourceDetail.enabled_tool_labels.length > 0
        ? selectedSourceDetail.enabled_tool_labels.join(", ")
        : "—",
    selectedSourceBaseProfile: selectedSourceDetail?.base_profile ?? "—",
    selectedSourceDiagnosticsSummary:
      formatToolRegistryProviderSourceDiagnosticsSummary(
        selectedSourceDetail?.diagnostics_summary,
      ),
    selectedSourceToolDetailsSummary: formatToolRegistryProviderToolDetailsSummary(
      selectedSourceDetail?.tool_details,
    ),
  };
}
