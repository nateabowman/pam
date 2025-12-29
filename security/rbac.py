"""
Role-Based Access Control (RBAC) for World P.A.M.
"""

from enum import Enum
from typing import Set, Optional, Dict
from dataclasses import dataclass
from logger import get_logger


class Role(str, Enum):
    """User roles."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


class Permission(str, Enum):
    """Permissions."""
    # Read permissions
    VIEW_SCENARIOS = "view_scenarios"
    VIEW_SIGNALS = "view_signals"
    VIEW_HISTORY = "view_history"
    VIEW_CONFIG = "view_config"
    
    # Write permissions
    EVALUATE_SCENARIOS = "evaluate_scenarios"
    MODIFY_CONFIG = "modify_config"
    MANAGE_USERS = "manage_users"
    MANAGE_API_KEYS = "manage_api_keys"
    
    # Admin permissions
    ADMIN_ACCESS = "admin_access"
    EXPORT_DATA = "export_data"
    DELETE_DATA = "delete_data"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.VIEW_SCENARIOS,
        Permission.VIEW_SIGNALS,
        Permission.VIEW_HISTORY,
        Permission.VIEW_CONFIG,
        Permission.EVALUATE_SCENARIOS,
        Permission.MODIFY_CONFIG,
        Permission.MANAGE_USERS,
        Permission.MANAGE_API_KEYS,
        Permission.ADMIN_ACCESS,
        Permission.EXPORT_DATA,
        Permission.DELETE_DATA,
    },
    Role.ANALYST: {
        Permission.VIEW_SCENARIOS,
        Permission.VIEW_SIGNALS,
        Permission.VIEW_HISTORY,
        Permission.VIEW_CONFIG,
        Permission.EVALUATE_SCENARIOS,
        Permission.EXPORT_DATA,
    },
    Role.VIEWER: {
        Permission.VIEW_SCENARIOS,
        Permission.VIEW_SIGNALS,
        Permission.VIEW_HISTORY,
    },
    Role.API_USER: {
        Permission.VIEW_SCENARIOS,
        Permission.VIEW_SIGNALS,
        Permission.VIEW_HISTORY,
        Permission.EVALUATE_SCENARIOS,
    },
}


@dataclass
class User:
    """User with role and permissions."""
    user_id: str
    username: str
    role: Role
    api_key_id: Optional[str] = None
    permissions: Optional[Set[Permission]] = None
    
    def __post_init__(self):
        """Set default permissions based on role."""
        if self.permissions is None:
            self.permissions = ROLE_PERMISSIONS.get(self.role, set())
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions


class RBACManager:
    """Manages role-based access control."""
    
    def __init__(self):
        self.logger = get_logger("rbac")
        self.users: Dict[str, User] = {}
        self.api_key_to_user: Dict[str, str] = {}
    
    def add_user(self, user: User):
        """Add a user to the system."""
        self.users[user.user_id] = user
        if user.api_key_id:
            self.api_key_to_user[user.api_key_id] = user.user_id
        self.logger.info(f"Added user: {user.username} with role: {user.role}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_api_key(self, api_key_id: str) -> Optional[User]:
        """Get user by API key ID."""
        user_id = self.api_key_to_user.get(api_key_id)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has permission."""
        user = self.get_user(user_id)
        if not user:
            return False
        return user.has_permission(permission)
    
    def require_permission(self, user_id: str, permission: Permission) -> bool:
        """
        Require permission, raise exception if not granted.
        
        Args:
            user_id: User ID
            permission: Required permission
            
        Returns:
            True if permission granted
            
        Raises:
            PermissionError: If permission denied
        """
        if not self.check_permission(user_id, permission):
            raise PermissionError(f"User {user_id} does not have permission: {permission}")
        return True


# Global RBAC manager
_global_rbac = RBACManager()


def get_rbac() -> RBACManager:
    """Get global RBAC manager."""
    return _global_rbac

