from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class TaskExecutionSlot:
    task_id: str
    _state: "TaskQueueState"
    _released: bool = False

    def release(self) -> None:
        if self._released:
            return
        self._state.release(self.task_id)
        self._released = True

    def __enter__(self) -> "TaskExecutionSlot":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()


class TaskQueueState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._active_task_ids: list[str] = []
        self._waiting_task_ids: list[str] = []

    def try_acquire(self, *, task_id: str, max_concurrent: int) -> TaskExecutionSlot | None:
        max_concurrent = _normalize_max_concurrent(max_concurrent)
        with self._lock:
            if task_id in self._active_task_ids:
                return TaskExecutionSlot(task_id=task_id, _state=self)
            if len(self._active_task_ids) >= max_concurrent:
                self._remember_waiting(task_id)
                return None
            self._forget_waiting(task_id)
            self._active_task_ids.append(task_id)
            return TaskExecutionSlot(task_id=task_id, _state=self)

    def release(self, task_id: str) -> None:
        with self._lock:
            self._forget_waiting(task_id)
            self._active_task_ids = [
                active_task_id
                for active_task_id in self._active_task_ids
                if active_task_id != task_id
            ]

    def snapshot(
        self,
        *,
        max_concurrent: int,
        task_id: str | None = None,
    ) -> dict[str, object]:
        max_concurrent = _normalize_max_concurrent(max_concurrent)
        with self._lock:
            active_task_ids = list(self._active_task_ids)
            waiting_task_ids = list(self._waiting_task_ids)
        wait_position: int | None
        if task_id in active_task_ids:
            wait_position = 0
        elif task_id in waiting_task_ids:
            wait_position = waiting_task_ids.index(task_id) + 1
        else:
            wait_position = None
        return {
            "active_count": len(active_task_ids),
            "max_concurrent": max_concurrent,
            "waiting_count": len(waiting_task_ids),
            "wait_position": wait_position,
        }

    def reset(self) -> None:
        with self._lock:
            self._active_task_ids.clear()
            self._waiting_task_ids.clear()

    def _remember_waiting(self, task_id: str) -> None:
        if task_id not in self._waiting_task_ids:
            self._waiting_task_ids.append(task_id)

    def _forget_waiting(self, task_id: str) -> None:
        self._waiting_task_ids = [
            waiting_task_id
            for waiting_task_id in self._waiting_task_ids
            if waiting_task_id != task_id
        ]


def _normalize_max_concurrent(max_concurrent: int) -> int:
    return max(1, int(max_concurrent or 1))


_TASK_QUEUE_STATE = TaskQueueState()


def try_acquire_task_execution_slot(
    *,
    task_id: str,
    max_concurrent: int,
) -> TaskExecutionSlot | None:
    return _TASK_QUEUE_STATE.try_acquire(
        task_id=task_id,
        max_concurrent=max_concurrent,
    )


def get_task_queue_snapshot(
    *,
    max_concurrent: int,
    task_id: str | None = None,
) -> dict[str, object]:
    return _TASK_QUEUE_STATE.snapshot(
        max_concurrent=max_concurrent,
        task_id=task_id,
    )


def release_task_execution_slot(task_id: str) -> None:
    _TASK_QUEUE_STATE.release(task_id)


def reset_task_queue_state_for_tests() -> None:
    _TASK_QUEUE_STATE.reset()
