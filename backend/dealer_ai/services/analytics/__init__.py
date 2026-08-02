"""Milestone 8 · Increment 1 (SESSION_094) — analytics aggregation package.

The read-only aggregation surface the M8 dashboards call into. Each
submodule owns one operational-question family from
``MILESTONE_8_PLANNING.md`` §1:

- :mod:`.acquisition` — Q1 (recon cost per source) + Q3 (vehicle-type
  profitability, deferred to M8.4).
- :mod:`.recon` — Q2 (vendor performance) + Q4 (repair-underestimate
  patterns) + Q7 (buyer estimate accuracy). All M8.2.
- :mod:`.lifecycle_aging` — Q5 (stage-aging trends) + Q9 (long-dwell
  stage patterns). Reads M7.3 ``StageAgingSnapshot`` rows. M8.3.
- :mod:`.sla_breaches` — Q10 (SLA-breach patterns). Reads M8.1
  ``SlaBreachRecord`` rows. M8.3.
- :mod:`.inventory_turn` — Q8 (days-to-sale proxy). M8.4.
- :mod:`.gross_profit` — Q6, deferred to Milestone 9 pending Sale
  substrate.

**Shape.** Every aggregation is a tenant-scoped module-level
function that takes a ``Dealership`` (required) plus keyword window
arguments and returns a list of frozen dataclass rows. **Read-only —
no aggregation ever writes.** Materialization (§5.a Option C
hybrid — user-confirmed at SESSION_094 open) is deferred until
operator evidence surfaces latency pain; today every call is
compute-on-request against live rows.

**Naming discipline.** The submodule name matches the domain of the
substrate it reads (``acquisition``, ``recon``, ``lifecycle_aging``,
``sla_breaches``) — NOT the M8 increment number. The M8 increment
sequencing is a delivery cadence; the domain is the enduring shape.

Public surface (re-exported here):

- :func:`recon_cost_per_source` — Q1 aggregation. First aggregation
  shipped at M8.1.
- :class:`SourcePerformanceRow` — its return row type.
- :func:`vendor_performance` — Q2 + Q4 aggregation. Shipped at M8.2.
- :class:`VendorPerformanceRow` — its return row type.
- :func:`stage_aging_trend` — Q5 + Q9 aggregation. Shipped at M8.3.
- :class:`AgingTrendPoint` — its return row type.
- :func:`breach_patterns` — Q10 aggregation. Shipped at M8.3.
- :class:`BreachPatternReport` — its return report type.
- :class:`VendorBreachCount` / :class:`KindBreachCount` — rollup
  sub-rows carried inside :class:`BreachPatternReport`.
- :func:`vehicle_type_recon_cost` — Q3 proxy aggregation. Shipped
  at M8.4.
- :class:`VehicleTypeReconCostRow` — its return row type.
- :func:`days_at_frontline_proxy` — Q8 proxy aggregation. Shipped
  at M8.4.
- :class:`DaysAtFrontlineReport` — its return report type.

Q7 (:func:`buyer_estimate_accuracy`) — deferred per
``MILESTONE_8_PLANNING.md`` §0.a (SESSION_095): substrate
(acquisition-buyer provenance) not yet shipped.

Q6 (gross-profit trend) — deferred to Milestone 9 per
``MILESTONE_8_PLANNING.md`` §1.6: substrate (Sale model) not yet
shipped.
"""

from __future__ import annotations

from .acquisition import (
    SourcePerformanceRow,
    VehicleTypeProfitabilityRow,
    VehicleTypeReconCostRow,
    recon_cost_per_source,
    vehicle_type_profitability,
    vehicle_type_recon_cost,
)
from .gross_profit import (
    GrossProfitPoint,
    gross_profit_trend,
)
from .lifecycle_aging import (
    AgingTrendPoint,
    DaysAtFrontlineReport,
    InventoryTurnReport,
    days_at_frontline_proxy,
    inventory_turn,
    stage_aging_trend,
)
from .recon import (
    BuyerAccuracyRow,
    VendorPerformanceRow,
    buyer_estimate_accuracy,
    vendor_performance,
)
from .sla_breaches import (
    BreachPatternReport,
    KindBreachCount,
    VendorBreachCount,
    breach_patterns,
)

__all__ = (
    "AgingTrendPoint",
    "BreachPatternReport",
    "BuyerAccuracyRow",
    "DaysAtFrontlineReport",
    "GrossProfitPoint",
    "InventoryTurnReport",
    "KindBreachCount",
    "SourcePerformanceRow",
    "VehicleTypeProfitabilityRow",
    "VehicleTypeReconCostRow",
    "VendorBreachCount",
    "VendorPerformanceRow",
    "breach_patterns",
    "buyer_estimate_accuracy",
    "days_at_frontline_proxy",
    "gross_profit_trend",
    "inventory_turn",
    "recon_cost_per_source",
    "stage_aging_trend",
    "vehicle_type_profitability",
    "vehicle_type_recon_cost",
    "vendor_performance",
)
