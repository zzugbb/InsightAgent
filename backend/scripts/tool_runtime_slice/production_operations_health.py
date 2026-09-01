from __future__ import annotations

from .context import SimpleNamespace


class ProductionOperationsHealthMixin:
    def test_production_operations_config_exposes_runbook_readiness_fields(
        self,
    ) -> None:
        config_module = __import__("app.config", fromlist=["Settings"])

        self.assertEqual(
            config_module.Settings.model_fields["operations_runbook_url"].alias,
            "INSIGHT_AGENT_OPERATIONS_RUNBOOK_URL",
        )
        self.assertEqual(
            config_module.Settings.model_fields["incident_contact"].alias,
            "INSIGHT_AGENT_INCIDENT_CONTACT",
        )
        self.assertEqual(
            config_module.Settings.model_fields["status_page_url"].alias,
            "INSIGHT_AGENT_STATUS_PAGE_URL",
        )
        self.assertEqual(
            config_module.Settings.model_fields["incident_last_drill_at"].alias,
            "INSIGHT_AGENT_INCIDENT_LAST_DRILL_AT",
        )

    def test_production_operations_health_flags_runbook_response_risks(
        self,
    ) -> None:
        operations_module = __import__(
            "app.services.operations_health",
            fromlist=["build_operations_health"],
        )

        payload = operations_module.build_operations_health(
            SimpleNamespace(
                app_env="production",
                mode="remote",
                provider="openai",
                api_key="configured-api-key",
                database_url="postgresql://insight:secret@db:5432/insightagent",
                cors_origins=["https://app.example.com"],
                chroma_probe=True,
                trace_persist_min_interval_sec=0.25,
                stream_reconnect_poll_fast_sec=0.3,
                stream_reconnect_poll_max_sec=2.0,
                stream_reconnect_heartbeat_interval_sec=2.0,
                task_timeout_sec=180.0,
                task_queue_max_concurrent=16,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
                task_execution_owner_id="backend-prod-a",
                task_execution_stale_after_sec=45.0,
                task_execution_heartbeat_interval_sec=2.0,
                auth_jwt_secret="prod-secret",
                auth_secret_key="separate-secret",
                backup_enabled=True,
                backup_provider="managed",
                backup_restore_runbook_url="https://runbooks.example.com/restore",
                backup_last_restore_drill_at="2099-01-01T00:00:00Z",
                operations_runbook_url="",
                incident_contact="",
                status_page_url="https://status.example.com/internal?token=raw",
            )
        )

        self.assertEqual(
            payload["runbook"],
            {
                "operations_runbook_configured": False,
                "incident_contact_configured": False,
                "status_page_configured": True,
                "incident_drill_recorded": False,
                "incident_drill_age_days": None,
                "incident_drill_max_age_days": 180,
                "incident_drill_recent": False,
            },
        )
        self.assertEqual(
            [warning["code"] for warning in payload["warnings"]],
            [
                "operations_runbook_missing",
                "incident_contact_missing",
            ],
        )
        self.assertNotIn("token=raw", str(payload))
        self.assertNotIn("status.example.com", str(payload))

    def test_production_operations_health_summarizes_warning_severity_counts(
        self,
    ) -> None:
        operations_module = __import__(
            "app.services.operations_health",
            fromlist=["build_operations_health"],
        )

        payload = operations_module.build_operations_health(
            SimpleNamespace(
                app_env="production",
                mode="remote",
                provider="openai",
                api_key=None,
                database_url="postgresql://insight:secret@127.0.0.1:5432/insightagent",
                cors_origins=["https://app.example.com", "*"],
                chroma_probe=False,
                trace_persist_min_interval_sec=0.25,
                stream_reconnect_poll_fast_sec=0.3,
                stream_reconnect_poll_max_sec=2.0,
                stream_reconnect_heartbeat_interval_sec=2.0,
                task_timeout_sec=180.0,
                task_queue_max_concurrent=16,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
                task_execution_owner_id="backend-prod-a",
                task_execution_stale_after_sec=45.0,
                task_execution_heartbeat_interval_sec=2.0,
                auth_jwt_secret="prod-secret",
                auth_secret_key="separate-secret",
                backup_enabled=True,
                backup_provider="managed",
                backup_restore_runbook_url="https://runbooks.example.com/restore",
                backup_last_restore_drill_at="2099-01-01T00:00:00Z",
                operations_runbook_url="https://runbooks.example.com/operations",
                incident_contact="oncall@example.com",
                incident_last_drill_at="2099-01-01T00:00:00Z",
                status_page_url="https://status.example.com/private?token=raw",
            )
        )

        self.assertEqual(
            payload["warning_summary"],
            {
                "total": 4,
                "critical": 2,
                "warning": 1,
                "info": 1,
                "highest_severity": "critical",
            },
        )
        self.assertEqual(
            payload["risk_domains"],
            {
                "deployment": {
                    "total": 3,
                    "critical": 2,
                    "warning": 1,
                    "info": 0,
                    "highest_severity": "critical",
                },
                "slo": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "backup_restore": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "runbook": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "runtime": {
                    "total": 1,
                    "critical": 0,
                    "warning": 0,
                    "info": 1,
                    "highest_severity": "info",
                },
            },
        )
        self.assertEqual(payload["readiness"], "attention")
        self.assertEqual(payload["readiness_level"], "critical")
        self.assertNotIn("token=raw", str(payload))

    def test_production_operations_health_summarizes_clean_warning_state(
        self,
    ) -> None:
        operations_module = __import__(
            "app.services.operations_health",
            fromlist=["build_operations_health"],
        )

        payload = operations_module.build_operations_health(
            SimpleNamespace(
                app_env="production",
                mode="remote",
                provider="openai",
                api_key="configured-api-key",
                database_url="postgresql://insight:secret@db:5432/insightagent",
                cors_origins=["https://app.example.com"],
                chroma_probe=True,
                trace_persist_min_interval_sec=0.25,
                stream_reconnect_poll_fast_sec=0.3,
                stream_reconnect_poll_max_sec=2.0,
                stream_reconnect_heartbeat_interval_sec=2.0,
                task_timeout_sec=180.0,
                task_queue_max_concurrent=16,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
                task_execution_owner_id="backend-prod-a",
                task_execution_stale_after_sec=45.0,
                task_execution_heartbeat_interval_sec=2.0,
                auth_jwt_secret="prod-secret",
                auth_secret_key="separate-secret",
                backup_enabled=True,
                backup_provider="managed",
                backup_restore_runbook_url="https://runbooks.example.com/restore",
                backup_last_restore_drill_at="2099-01-01T00:00:00Z",
                operations_runbook_url="https://runbooks.example.com/operations",
                incident_contact="oncall@example.com",
                incident_last_drill_at="2099-01-01T00:00:00Z",
                status_page_url="https://status.example.com",
            )
        )

        self.assertEqual(
            payload["warning_summary"],
            {
                "total": 0,
                "critical": 0,
                "warning": 0,
                "info": 0,
                "highest_severity": None,
            },
        )
        self.assertEqual(
            payload["risk_domains"],
            {
                "deployment": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "slo": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "backup_restore": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "runbook": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
                "runtime": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0,
                    "highest_severity": None,
                },
            },
        )
        self.assertEqual(payload["readiness"], "ok")
        self.assertEqual(payload["readiness_level"], "ok")

    def test_production_operations_health_marks_info_only_readiness_level(
        self,
    ) -> None:
        operations_module = __import__(
            "app.services.operations_health",
            fromlist=["build_operations_health"],
        )

        payload = operations_module.build_operations_health(
            SimpleNamespace(
                app_env="production",
                mode="remote",
                provider="openai",
                api_key="configured-api-key",
                database_url="postgresql://insight:secret@db:5432/insightagent",
                cors_origins=["https://app.example.com"],
                chroma_probe=True,
                trace_persist_min_interval_sec=0.25,
                stream_reconnect_poll_fast_sec=0.3,
                stream_reconnect_poll_max_sec=2.0,
                stream_reconnect_heartbeat_interval_sec=2.0,
                task_timeout_sec=180.0,
                task_queue_max_concurrent=16,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
                task_execution_owner_id="backend-prod-a",
                task_execution_stale_after_sec=45.0,
                task_execution_heartbeat_interval_sec=2.0,
                auth_jwt_secret="prod-secret",
                auth_secret_key="separate-secret",
                backup_enabled=True,
                backup_provider="managed",
                backup_restore_runbook_url="https://runbooks.example.com/restore",
                backup_last_restore_drill_at="2099-01-01T00:00:00Z",
                operations_runbook_url="https://runbooks.example.com/operations",
                incident_contact="oncall@example.com",
                incident_last_drill_at="2099-01-01T00:00:00Z",
                status_page_url="",
            )
        )

        self.assertEqual(payload["readiness"], "attention")
        self.assertEqual(payload["readiness_level"], "info")
        self.assertEqual(payload["warning_summary"]["highest_severity"], "info")

    def test_production_operations_health_flags_missing_incident_drill(
        self,
    ) -> None:
        operations_module = __import__(
            "app.services.operations_health",
            fromlist=["build_operations_health"],
        )

        payload = operations_module.build_operations_health(
            SimpleNamespace(
                app_env="production",
                mode="remote",
                provider="openai",
                api_key="configured-api-key",
                database_url="postgresql://insight:secret@db:5432/insightagent",
                cors_origins=["https://app.example.com"],
                chroma_probe=True,
                trace_persist_min_interval_sec=0.25,
                stream_reconnect_poll_fast_sec=0.3,
                stream_reconnect_poll_max_sec=2.0,
                stream_reconnect_heartbeat_interval_sec=2.0,
                task_timeout_sec=180.0,
                task_queue_max_concurrent=16,
                task_queue_max_concurrent_per_user=0,
                task_queue_max_concurrent_per_session=0,
                task_queue_poll_interval_sec=0.25,
                task_execution_owner_id="backend-prod-a",
                task_execution_stale_after_sec=45.0,
                task_execution_heartbeat_interval_sec=2.0,
                auth_jwt_secret="prod-secret",
                auth_secret_key="separate-secret",
                backup_enabled=True,
                backup_provider="managed",
                backup_restore_runbook_url="https://runbooks.example.com/restore",
                backup_last_restore_drill_at="2099-01-01T00:00:00Z",
                operations_runbook_url="https://runbooks.example.com/operations",
                incident_contact="oncall@example.com",
                incident_last_drill_at="",
                status_page_url="https://status.example.com/private?token=raw",
            )
        )

        self.assertEqual(
            payload["runbook"],
            {
                "operations_runbook_configured": True,
                "incident_contact_configured": True,
                "status_page_configured": True,
                "incident_drill_recorded": False,
                "incident_drill_age_days": None,
                "incident_drill_max_age_days": 180,
                "incident_drill_recent": False,
            },
        )
        self.assertEqual(
            [warning["code"] for warning in payload["warnings"]],
            ["incident_response_drill_missing"],
        )
        self.assertEqual(payload["risk_domains"]["runbook"]["total"], 1)
        self.assertEqual(
            payload["risk_domains"]["runbook"]["highest_severity"],
            "warning",
        )
        self.assertEqual(payload["readiness_level"], "warning")
        self.assertNotIn("token=raw", str(payload))
        self.assertNotIn("status.example.com", str(payload))
