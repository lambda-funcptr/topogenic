from dataclasses import dataclass
from typing import Any, Optional, TypeAlias, Union

from .db import Entity, Scope

@dataclass
class Debug():
    level: int
    message: str
    data: Optional[dict[str, Any]] = None

    def __repl__():
        return "{message}"


Operation: TypeAlias = Union[Debug, Entity, Scope, Scope.Meta, Scope.End]
