from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    roles: list[str] = field(default_factory=list)
    email: str | None = None
    auth_mode: str = "jwt"
    claims: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, allowed_roles: list[str] | tuple[str, ...] | set[str]) -> bool:
        return any(role in self.roles for role in allowed_roles)
