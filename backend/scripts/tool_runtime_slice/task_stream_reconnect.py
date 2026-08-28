from __future__ import annotations

from .context import asyncio, SimpleNamespace, task_routes_module


class TaskStreamReconnectMixin:
    def test_stream_running_task_reconnect_uses_failed_task_error_event_hint(
        self,
    ) -> None:
        original_get_settings = task_routes_module.get_settings
        original_get_task = task_routes_module.get_task
        original_delta_snapshot_loader = getattr(
            task_routes_module.chat_persistence_service,
            "get_task_trace_delta_snapshot_from_task",
            None,
        )
        try:
            task_routes_module.get_settings = lambda: SimpleNamespace(
                stream_reconnect_poll_fast_sec=0.05,
                stream_reconnect_poll_max_sec=0.5,
                stream_reconnect_heartbeat_interval_sec=1.0,
            )
            task_routes_module.get_task = lambda _task_id, _user_id: {
                "id": "task-reconnect-remote-network-error",
                "session_id": "session-reconnect-remote-network-error",
                "status": "failed",
                "trace_json": "[]",
                "failure_hint": "remote_provider_network_error",
                "failure_source": "error_event",
            }
            task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = (  # type: ignore[attr-defined]
                lambda _task, after_seq=0, limit=200: (
                    [],
                    after_seq,
                    False,
                    0,
                    None,
                )
            )

            async def collect_events() -> list[str]:
                events: list[str] = []
                async for event in task_routes_module.stream_running_task_reconnect(
                    "task-reconnect-remote-network-error",
                    "user-reconnect-remote-network-error",
                ):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())
        finally:
            task_routes_module.get_settings = original_get_settings
            task_routes_module.get_task = original_get_task
            if original_delta_snapshot_loader is None:
                if hasattr(
                    task_routes_module.chat_persistence_service,
                    "get_task_trace_delta_snapshot_from_task",
                ):
                    delattr(
                        task_routes_module.chat_persistence_service,
                        "get_task_trace_delta_snapshot_from_task",
                    )
            else:
                task_routes_module.chat_persistence_service.get_task_trace_delta_snapshot_from_task = original_delta_snapshot_loader  # type: ignore[attr-defined]

        self.assertGreaterEqual(len(events), 3)
        self.assertIn('"phase": "error"', events[-2])
        self.assertIn('"code": "remote_provider_network_error"', events[-1])
        self.assertIn("Remote provider stream network error.", events[-1])
