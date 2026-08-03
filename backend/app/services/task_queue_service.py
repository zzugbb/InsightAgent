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


@dataclass(frozen=True)
class TaskQueueScope:
    user_id: str | None = None
    session_id: str | None = None


class TaskQueueState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._active_task_ids: list[str] = []
        self._waiting_task_ids: list[str] = []
        self._task_scopes: dict[str, TaskQueueScope] = {}

    def try_acquire(
        self,
        *,
        task_id: str,
        max_concurrent: int,
        user_id: str | None = None,
        session_id: str | None = None,
        max_concurrent_per_user: int | None = None,
        max_concurrent_per_session: int | None = None,
    ) -> TaskExecutionSlot | None:
        max_concurrent = _normalize_max_concurrent(max_concurrent)
        max_concurrent_per_user = _normalize_optional_limit(max_concurrent_per_user)
        max_concurrent_per_session = _normalize_optional_limit(
            max_concurrent_per_session
        )
        scope = TaskQueueScope(
            user_id=_normalize_scope_value(user_id),
            session_id=_normalize_scope_value(session_id),
        )
        with self._lock:
            if task_id in self._active_task_ids:
                return TaskExecutionSlot(task_id=task_id, _state=self)
            if (
                len(self._active_task_ids) >= max_concurrent
                or self._scope_limit_reached(
                    scope=scope,
                    max_concurrent_per_user=max_concurrent_per_user,
                    max_concurrent_per_session=max_concurrent_per_session,
                )
                or self._older_eligible_waiting_count(
                    task_id=task_id,
                    max_concurrent_per_user=max_concurrent_per_user,
                    max_concurrent_per_session=max_concurrent_per_session,
                )
                >= (max_concurrent - len(self._active_task_ids))
            ):
                self._remember_waiting(task_id, scope)
                return None
            self._forget_waiting(task_id)
            self._task_scopes[task_id] = scope
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
            self._task_scopes.pop(task_id, None)

    def forget_waiting(self, task_id: str) -> None:
        with self._lock:
            self._forget_waiting(task_id)

    def snapshot(
        self,
        *,
        max_concurrent: int,
        task_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        max_concurrent = _normalize_max_concurrent(max_concurrent)
        scope = TaskQueueScope(
            user_id=_normalize_scope_value(user_id),
            session_id=_normalize_scope_value(session_id),
        )
        with self._lock:
            active_task_ids = list(self._active_task_ids)
            waiting_task_ids = list(self._waiting_task_ids)
            task_scopes = dict(self._task_scopes)
        wait_position: int | None
        if task_id in active_task_ids:
            wait_position = 0
        elif task_id in waiting_task_ids:
            wait_position = waiting_task_ids.index(task_id) + 1
        else:
            wait_position = None
        snapshot: dict[str, object] = {
            "active_count": len(active_task_ids),
            "max_concurrent": max_concurrent,
            "waiting_count": len(waiting_task_ids),
            "wait_position": wait_position,
        }
        if scope.user_id:
            snapshot["active_count_for_user"] = _count_tasks_for_scope(
                active_task_ids,
                task_scopes=task_scopes,
                user_id=scope.user_id,
            )
            snapshot["waiting_count_for_user"] = _count_tasks_for_scope(
                waiting_task_ids,
                task_scopes=task_scopes,
                user_id=scope.user_id,
            )
        if scope.session_id:
            snapshot["active_count_for_session"] = _count_tasks_for_scope(
                active_task_ids,
                task_scopes=task_scopes,
                session_id=scope.session_id,
            )
            snapshot["waiting_count_for_session"] = _count_tasks_for_scope(
                waiting_task_ids,
                task_scopes=task_scopes,
                session_id=scope.session_id,
            )
        return snapshot

    def reset(self) -> None:
        with self._lock:
            self._active_task_ids.clear()
            self._waiting_task_ids.clear()
            self._task_scopes.clear()

    def _remember_waiting(self, task_id: str, scope: TaskQueueScope) -> None:
        self._task_scopes[task_id] = scope
        if task_id not in self._waiting_task_ids:
            self._waiting_task_ids.append(task_id)

    def _forget_waiting(self, task_id: str) -> None:
        self._waiting_task_ids = [
            waiting_task_id
            for waiting_task_id in self._waiting_task_ids
            if waiting_task_id != task_id
        ]
        if task_id not in self._active_task_ids:
            self._task_scopes.pop(task_id, None)

    def _scope_limit_reached(
        self,
        *,
        scope: TaskQueueScope,
        max_concurrent_per_user: int | None,
        max_concurrent_per_session: int | None,
    ) -> bool:
        if (
            max_concurrent_per_user is not None
            and scope.user_id
            and self._active_count_for_scope(user_id=scope.user_id)
            >= max_concurrent_per_user
        ):
            return True
        if (
            max_concurrent_per_session is not None
            and scope.session_id
            and self._active_count_for_scope(session_id=scope.session_id)
            >= max_concurrent_per_session
        ):
            return True
        return False

    def _active_count_for_scope(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> int:
        count = 0
        for task_id in self._active_task_ids:
            scope = self._task_scopes.get(task_id)
            if scope is None:
                continue
            if user_id is not None and scope.user_id == user_id:
                count += 1
            elif session_id is not None and scope.session_id == session_id:
                count += 1
        return count

    def _older_eligible_waiting_count(
        self,
        *,
        task_id: str,
        max_concurrent_per_user: int | None,
        max_concurrent_per_session: int | None,
    ) -> int:
        count = 0
        for waiting_task_id in self._waiting_task_ids:
            if waiting_task_id == task_id:
                return count
            waiting_scope = self._task_scopes.get(waiting_task_id, TaskQueueScope())
            if not self._scope_limit_reached(
                scope=waiting_scope,
                max_concurrent_per_user=max_concurrent_per_user,
                max_concurrent_per_session=max_concurrent_per_session,
            ):
                count += 1
        return count


def _normalize_max_concurrent(max_concurrent: int) -> int:
    return max(1, int(max_concurrent or 1))


def _normalize_optional_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    normalized = int(limit or 0)
    if normalized <= 0:
        return None
    return normalized


def _normalize_scope_value(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _count_tasks_for_scope(
    task_ids: list[str],
    *,
    task_scopes: dict[str, TaskQueueScope],
    user_id: str | None = None,
    session_id: str | None = None,
) -> int:
    count = 0
    for task_id in task_ids:
        scope = task_scopes.get(task_id)
        if scope is None:
            continue
        if user_id is not None and scope.user_id == user_id:
            count += 1
            continue
        if session_id is not None and scope.session_id == session_id:
            count += 1
    return count


_TASK_QUEUE_STATE = TaskQueueState()


def try_acquire_task_execution_slot(
    *,
    task_id: str,
    max_concurrent: int,
    user_id: str | None = None,
    session_id: str | None = None,
    max_concurrent_per_user: int | None = None,
    max_concurrent_per_session: int | None = None,
) -> TaskExecutionSlot | None:
    return _TASK_QUEUE_STATE.try_acquire(
        task_id=task_id,
        max_concurrent=max_concurrent,
        user_id=user_id,
        session_id=session_id,
        max_concurrent_per_user=max_concurrent_per_user,
        max_concurrent_per_session=max_concurrent_per_session,
    )


def get_task_queue_snapshot(
    *,
    max_concurrent: int,
    task_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, object]:
    return _TASK_QUEUE_STATE.snapshot(
        max_concurrent=max_concurrent,
        task_id=task_id,
        user_id=user_id,
        session_id=session_id,
    )


def release_task_execution_slot(task_id: str) -> None:
    _TASK_QUEUE_STATE.release(task_id)


def forget_waiting_task(task_id: str) -> None:
    _TASK_QUEUE_STATE.forget_waiting(task_id)


def reset_task_queue_state_for_tests() -> None:
    _TASK_QUEUE_STATE.reset()
