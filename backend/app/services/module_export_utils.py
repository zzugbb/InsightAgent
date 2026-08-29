from __future__ import annotations

from types import FunctionType, ModuleType


def clone_function_for_namespace(
    function: FunctionType,
    namespace: dict[str, object],
) -> FunctionType:
    rebound = FunctionType(
        function.__code__,
        namespace,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    rebound.__kwdefaults__ = function.__kwdefaults__
    rebound.__annotations__ = dict(function.__annotations__)
    rebound.__dict__.update(function.__dict__)
    rebound.__doc__ = function.__doc__
    rebound.__module__ = str(namespace.get("__name__", function.__module__))
    return rebound


def install_rebound_exports(
    *,
    source_module: ModuleType,
    target_namespace: dict[str, object],
    export_names: tuple[str, ...],
) -> None:
    for export_name in export_names:
        value = getattr(source_module, export_name)
        if isinstance(value, FunctionType):
            value = clone_function_for_namespace(value, target_namespace)
        target_namespace[export_name] = value
