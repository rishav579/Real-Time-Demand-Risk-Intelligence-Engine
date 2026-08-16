"""Risk scoring, simulation, root-cause attribution, and prescriptive recommendations package."""

from src.risk.attribution import (
    RootCauseCategory,
    attribute_node_root_cause,
    compute_root_cause_attribution,
)
from src.risk.recommendations import (
    ActionRecommendation,
    ActionType,
    PriorityTier,
    generate_prescriptive_recommendations,
)
from src.risk.risk_scoring import (
    StockoutRiskTier,
    calculate_stockout_risk_score,
    classify_stockout_tier,
    compute_risk_scoring,
)
from src.risk.safety_stock import (
    Z_SERVICE_LEVELS,
    calculate_safety_stock,
    compute_node_reorder_points,
)
from src.risk.simulation import (
    DailySimulationStep,
    RunoutSimulationResult,
    simulate_network_runout,
    simulate_node_runout,
)

__all__ = [
    # Simulation
    "DailySimulationStep",
    "RunoutSimulationResult",
    "simulate_node_runout",
    "simulate_network_runout",
    # Safety Stock & ROP
    "Z_SERVICE_LEVELS",
    "calculate_safety_stock",
    "compute_node_reorder_points",
    # Risk Scoring
    "StockoutRiskTier",
    "calculate_stockout_risk_score",
    "classify_stockout_tier",
    "compute_risk_scoring",
    # Attribution
    "RootCauseCategory",
    "attribute_node_root_cause",
    "compute_root_cause_attribution",
    # Prescriptive Recommendations
    "ActionType",
    "PriorityTier",
    "ActionRecommendation",
    "generate_prescriptive_recommendations",
]
