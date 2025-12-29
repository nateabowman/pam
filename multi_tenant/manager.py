"""
Multi-tenancy support for World P.A.M.
"""

from typing import Optional, Dict, Any
from logger import get_logger


class TenantManager:
    """Manages multi-tenant data isolation."""
    
    def __init__(self):
        self.tenants: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("tenant_manager")
    
    def create_tenant(self, tenant_id: str, config: Dict[str, Any]):
        """Create a new tenant."""
        self.tenants[tenant_id] = config
        self.logger.info(f"Created tenant: {tenant_id}")
    
    def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration."""
        return self.tenants.get(tenant_id)
    
    def isolate_query(self, query: str, tenant_id: str) -> str:
        """
        Modify query to include tenant isolation.
        
        Args:
            query: SQL query
            tenant_id: Tenant ID
            
        Returns:
            Modified query with tenant filter
        """
        # Add tenant_id filter to query
        # This is a simplified example
        if "WHERE" in query.upper():
            return query + f" AND tenant_id = '{tenant_id}'"
        else:
            return query + f" WHERE tenant_id = '{tenant_id}'"

