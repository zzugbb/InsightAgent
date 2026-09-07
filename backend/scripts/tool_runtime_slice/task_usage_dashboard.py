from __future__ import annotations

from .task_usage_dashboard_part1 import TaskUsageDashboardMixinPart1
from .task_usage_dashboard_part2 import TaskUsageDashboardMixinPart2


class TaskUsageDashboardMixin(
    TaskUsageDashboardMixinPart1,
    TaskUsageDashboardMixinPart2,
):
    pass
