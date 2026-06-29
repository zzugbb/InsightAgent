import type {
  SettingsSummary,
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

export function formatToolRegistryProviderToolDetailsSummary(
  toolDetails: ToolRegistryProviderToolDetail[] | undefined,
): string {
  if (!toolDetails || toolDetails.length === 0) {
    return "—";
  }
  return toolDetails
    .map((tool) => {
      const semanticOrKind =
        typeof tool.semantic_kind === "string" && tool.semantic_kind.trim().length > 0
          ? tool.semantic_kind.trim()
          : tool.kind;
      const previewKeys =
        Array.isArray(tool.effective_result_preview_keys)
          ? tool.effective_result_preview_keys.filter((key) => key.trim().length > 0)
          : [];
      const outputKeys =
        Array.isArray(tool.effective_result_output_keys)
          ? tool.effective_result_output_keys.filter((key) => key.trim().length > 0)
          : [];
      if (previewKeys.length === 0 && outputKeys.length === 0) {
        return `${tool.label} [${semanticOrKind}]`;
      }
      if (previewKeys.length > 0 && outputKeys.length > 0) {
        return `${tool.label} [${semanticOrKind}]: preview ${previewKeys.join(", ")}; output ${outputKeys.join(", ")}`;
      }
      if (previewKeys.length > 0) {
        return `${tool.label} [${semanticOrKind}]: ${previewKeys.join(", ")}`;
      }
      return `${tool.label} [${semanticOrKind}]: output ${outputKeys.join(", ")}`;
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
    selectedSourceToolDetailsSummary: formatToolRegistryProviderToolDetailsSummary(
      selectedSourceDetail?.tool_details,
    ),
  };
}
