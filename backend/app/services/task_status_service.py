from typing import Literal

TaskStatusNormalized = Literal["pending", "running", "completed", "failed", "other"]


def normalize_task_status(status: str) -> TaskStatusNormalized:
    s = status.strip().lower()
    if s == "pending":
        return "pending"
    if s == "running":
        return "running"
    if s in ("completed", "done", "success"):
        return "completed"
    if s in ("failed", "error"):
        return "failed"
    return "other"


def task_status_label(status: str) -> str:
    normalized = normalize_task_status(status)
    if normalized == "pending":
        return "Pending"
    if normalized == "running":
        return "Running"
    if normalized == "completed":
        return "Completed"
    if normalized == "failed":
        return "Failed"
    return "Other"


def task_status_rank(status: str) -> int:
    """
    统一状态顺序（用于前端可选排序或分组）：
    pending < running < failed < completed < other
    """
    normalized = normalize_task_status(status)
    if normalized == "pending":
        return 10
    if normalized == "running":
        return 20
    if normalized == "failed":
        return 30
    if normalized == "completed":
        return 40
    return 99
