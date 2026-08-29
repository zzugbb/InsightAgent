from __future__ import annotations

from .settings_registry_part1 import SettingsRegistryMixinPart1
from .settings_registry_part2 import SettingsRegistryMixinPart2


class SettingsRegistryMixin(SettingsRegistryMixinPart1, SettingsRegistryMixinPart2):
    pass
