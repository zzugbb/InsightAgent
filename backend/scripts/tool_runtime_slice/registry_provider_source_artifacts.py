from __future__ import annotations

from .context import *


class RegistryProviderSourceArtifactsMixin:
    def _make_sensitive_preflight_summary_model(
        self,
    ) -> object:
        return tool_runtime_module.ConfiguredToolRegistryProviderPreflightSummaryModel(
            provider_source_name="suite_api_key=hidden",
            tool_count=1,
            tool_names=("calc_eval",),
            tool_details=(
                {
                    "name": "calc_eval",
                    "diagnostics": {
                        "provider_source": "suite_api_key=hidden",
                    },
                },
            ),
            service_action_count=0,
            service_action_kinds=(),
            trace_write_count=0,
            audit_event_count=0,
            has_diagnostics=True,
            diagnostics_total=1,
            skipped_total=0,
            missing_total=1,
            diagnostics_summary={
                "has_diagnostics": True,
                "total": 1,
                "skipped_total": 0,
                "missing_total": 1,
                "entries": (
                    {
                        "kind": "missing",
                        "target": "registry_sources",
                        "count": 1,
                        "values": ("suite_api_key=hidden",),
                        "detail": {
                            "provider_source": "suite_api_key=hidden",
                        },
                    },
                ),
            },
        )

    def test_preflight_summary_model_to_dict_redacts_provider_source_artifacts(
        self,
    ) -> None:
        summary_model = self._make_sensitive_preflight_summary_model()

        result = summary_model.to_dict()

        self.assertEqual(result["provider_source_name"], "suite_[redacted]")
        self.assertEqual(
            result["tool_details"][0]["diagnostics"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            result["diagnostics_summary"]["entries"][0]["values"],
            ("suite_[redacted]",),
        )
        self.assertEqual(
            result["diagnostics_summary"]["entries"][0]["detail"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertNotIn("api_key=hidden", json.dumps(result, default=str))

    def test_preflight_result_model_to_dict_redacts_summary_provider_source_artifacts(
        self,
    ) -> None:
        provider = StaticToolRegistryProvider(
            {"calc_eval": get_default_tool_registry()["calc_eval"]}
        )
        diagnostics_runtime = tool_runtime_module.ToolRegistryDiagnosticsRuntimeArtifactsModel(
            summary=build_tool_registry_diagnostics_summary_model(diagnostics={}),
            trace_step=None,
            trace_event=None,
            audit_detail=None,
        )
        runtime_artifacts = tool_runtime_module.ConfiguredToolRegistryProviderRuntimeArtifactsModel(
            provider=provider,
            provider_source_name="suite_api_key=hidden",
            provider_sources={"suite_api_key=hidden": provider},
            selected_source_diagnostics={},
            source_diagnostics={},
            diagnostics_runtime=diagnostics_runtime,
            audit_event=None,
        )
        service_execution = tool_runtime_module.ConfiguredToolRegistryProviderServiceExecutionModel(
            provider=provider,
            provider_source_name="suite_api_key=hidden",
            runtime_artifacts=runtime_artifacts,
            service_actions=(),
        )
        result_model = tool_runtime_module.ConfiguredToolRegistryProviderPreflightResultModel(
            provider=provider,
            provider_source_name="suite_api_key=hidden",
            runtime_artifacts=runtime_artifacts,
            service_execution=service_execution,
            trace_write_count=0,
            audit_event_count=0,
            summary=self._make_sensitive_preflight_summary_model(),
        )

        result = result_model.to_dict()

        self.assertEqual(result["provider_source_name"], "suite_[redacted]")
        self.assertEqual(
            result["summary"]["tool_details"][0]["diagnostics"]["provider_source"],
            "suite_[redacted]",
        )
        self.assertEqual(
            result["summary"]["diagnostics_summary"]["entries"][0]["values"],
            ("suite_[redacted]",),
        )
        self.assertNotIn("api_key=hidden", json.dumps(result, default=str))
