from __future__ import annotations

from .http_json_mapping_part1 import HttpJsonMappingMixinPart1
from .http_json_mapping_part2 import HttpJsonMappingMixinPart2


class HttpJsonMappingMixin(HttpJsonMappingMixinPart1, HttpJsonMappingMixinPart2):
    pass
