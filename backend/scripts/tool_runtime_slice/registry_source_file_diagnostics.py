from __future__ import annotations

from .registry_source_file_diagnostics_part1 import (
    RegistrySourceFileDiagnosticsMixinPart1,
)
from .registry_source_file_diagnostics_part2 import (
    RegistrySourceFileDiagnosticsMixinPart2,
)


class RegistrySourceFileDiagnosticsMixin(
    RegistrySourceFileDiagnosticsMixinPart1,
    RegistrySourceFileDiagnosticsMixinPart2,
):
    pass
