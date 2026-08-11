"""Composition rules for report dependency envelopes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .result import Result


@dataclass(frozen=True)
class Dependency:
    name: str
    result: Result[Any]
    required: bool
    empty_is_unexpected: bool = False


def reduce_dependencies(
    dependencies: Iterable[Dependency], output_items: list[Any]
) -> tuple[str, str, dict[str, Any]]:
    deps = list(dependencies)
    required = [dep for dep in deps if dep.required]
    if not output_items:
        if any(dep.result.status == "error" for dep in required):
            status = "error"
        elif any(dep.result.status == "unsupported" for dep in required):
            status = "unsupported"
        elif required and all(dep.result.status == "empty" for dep in required):
            status = "empty"
        else:
            status = "empty"
    else:
        degraded = [
            dep.name
            for dep in deps
            if dep.result.status == "partial"
            or dep.result.status in {"error", "unsupported"}
            or (dep.result.status == "empty" and (dep.required or dep.empty_is_unexpected))
        ]
        status = "partial" if degraded else "ok"
    degraded = [
        dep.name
        for dep in deps
        if dep.result.status not in {"ok"}
        and not (dep.result.status == "empty" and not dep.required and not dep.empty_is_unexpected)
    ]
    reason = f"Degraded dependencies: {', '.join(degraded)}" if degraded else ""
    metadata = {"dependencies": {dep.name: dep.result.to_dict() for dep in deps}}
    return status, reason, metadata
