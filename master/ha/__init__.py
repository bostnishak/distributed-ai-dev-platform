"""EPK-10 & EPK-30 High Availability package: leader leases, node drain & idempotent result commits."""

from ha.leader import (
    acquire_or_renew_lease,
    commit_idempotent_result,
    compute_amdahl_speedup_matrix,
    drain_leader_node,
    get_ha_status,
    init_ha_db,
    router,
)

__all__ = [
    "acquire_or_renew_lease",
    "commit_idempotent_result",
    "compute_amdahl_speedup_matrix",
    "drain_leader_node",
    "get_ha_status",
    "init_ha_db",
    "router",
]
