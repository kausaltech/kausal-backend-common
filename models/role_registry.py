from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kausal_common.models.roles import InstanceSpecificRole


class RoleRegistry:
    def __init__(self):
        self.roles: dict[str, InstanceSpecificRole] = {}

    def register(self, role: InstanceSpecificRole):
        """Register a role in the role registry."""
        from .roles import InstanceSpecificRole

        if not isinstance(role, InstanceSpecificRole):
            msg = f"Only InstanceSpecificRole instances can be registered. Got {role}"
            raise TypeError(msg)

        if role.id in self.roles:
            msg = f"Role with id '{role.id}' is already registered"
            raise ValueError(msg)

        self.roles[role.id] = role

    def get_role(self, role_id: str) -> InstanceSpecificRole:
        """Get a role by its ID."""
        if role_id not in self.roles:
            msg = f"No role registered with id '{role_id}'"
            raise KeyError(msg)
        return self.roles[role_id]

    def get_all_roles(self) -> list[InstanceSpecificRole]:
        """Get all registered roles."""
        return list(self.roles.values())


# Create a global instance of RoleRegistry
role_registry = RoleRegistry()


def register_role(role: InstanceSpecificRole):
    return role_registry.register(role)
