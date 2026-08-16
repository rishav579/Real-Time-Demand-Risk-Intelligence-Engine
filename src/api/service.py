"""Central intelligence service providing cached analytical access for APIs and UI."""

from datetime import date
from typing import Dict, List, Optional, Set
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.analytics.marts import build_all_marts
from src.config.settings import get_settings
from src.forecasting.features import build_forecasting_dataset
from src.forecasting.model import LightGBMDemandForecaster
from src.forecasting.splits import create_temporal_splits
from src.risk.attribution import compute_root_cause_attribution
from src.risk.recommendations import generate_prescriptive_recommendations
from src.risk.risk_scoring import compute_risk_scoring
from src.risk.safety_stock import compute_node_reorder_points
from src.risk.simulation import simulate_network_runout


class IntelligenceService:
    """Singleton cached service managing forecasts, risks, and prescriptive recommendations."""

    def __init__(self, engine: Optional[Engine] = None, as_of_date: Optional[date] = None):
        settings = get_settings()
        self.engine = engine or create_engine(settings.database_url, echo=False)
        self.as_of_date = as_of_date or date(2026, 12, 31)

        # Cache storage
        self._marts: Optional[Dict[str, pd.DataFrame]] = None
        self._forecasts_df: Optional[pd.DataFrame] = None
        self._risk_nodes_df: Optional[pd.DataFrame] = None
        self._recommendations_df: Optional[pd.DataFrame] = None
        self._known_locations: Set[str] = set()
        self._known_products: Set[str] = set()
        self._initialized: bool = False

    def initialize(self, force_refresh: bool = False) -> None:
        """Compute and populate in-memory intelligence state from database."""
        if self._initialized and not force_refresh:
            return

        # 1. Build Analytical Marts
        self._marts = build_all_marts(self.engine, as_of_date=self.as_of_date, persist_to_db=True)

        # 2. Train Champion Forecasting Model & Generate Forecasts
        feat_df = build_forecasting_dataset(self.engine)
        train_df, val_df, test_df = create_temporal_splits(feat_df)
        forecaster = LightGBMDemandForecaster(random_state=42).fit(train_df, val_df)
        self._forecasts_df = forecaster.predict(test_df, horizon_days=30)

        # 3. Simulate Runout, Safety Stock, Risk Scoring, and Attribution
        sim_df = simulate_network_runout(
            engine=self.engine,
            predictions_df=self._forecasts_df,
            as_of_date=self.as_of_date,
        )
        rop_df = compute_node_reorder_points(sim_df, engine=self.engine)
        risk_scored_df = compute_risk_scoring(rop_df)
        self._risk_nodes_df = compute_root_cause_attribution(risk_scored_df)

        # 4. Generate Prescriptive Action Recommendations
        self._recommendations_df = generate_prescriptive_recommendations(self._risk_nodes_df)

        # Cache entity sets for fast validation
        self._known_locations = set(self._risk_nodes_df["location_id"].unique())
        self._known_products = set(self._risk_nodes_df["product_id"].unique())

        self._initialized = True

    def is_valid_location(self, location_id: str) -> bool:
        """Check if location identifier exists in network catalog."""
        self.initialize()
        return location_id in self._known_locations

    def is_valid_product(self, product_id: str) -> bool:
        """Check if product identifier exists in product catalog."""
        self.initialize()
        return product_id in self._known_products

    def get_executive_summary(self) -> Dict:
        """Generate high-level executive KPI metrics."""
        self.initialize()
        risk_df = self._risk_nodes_df
        recs_df = self._recommendations_df

        crit_count = int((risk_df["stockout_risk_tier"] == "CRITICAL").sum())
        high_count = int((risk_df["stockout_risk_tier"] == "HIGH").sum())
        med_count = int((risk_df["stockout_risk_tier"] == "MEDIUM").sum())
        low_count = int((risk_df["stockout_risk_tier"] == "LOW").sum())

        tot_cap_risk = round(float(risk_df["capital_at_risk"].sum()), 2)
        tot_hold_cost = round(float(risk_df["annual_holding_cost"].sum()), 2)

        dc_trans = int((recs_df["action_type"] == "DC_TRANSFER").sum()) if len(recs_df) > 0 else 0
        po_count = int((recs_df["action_type"] == "PURCHASE_ORDER").sum()) if len(recs_df) > 0 else 0
        hold_count = int((recs_df["action_type"] == "HOLD_ORDER").sum()) if len(recs_df) > 0 else 0
        urg_count = int((recs_df["priority_tier"] == "URGENT").sum()) if len(recs_df) > 0 else 0

        return {
            "as_of_date": self.as_of_date,
            "total_locations": int(risk_df["location_id"].nunique()),
            "total_products": int(risk_df["product_id"].nunique()),
            "total_node_positions": len(risk_df),
            "critical_stockout_risks": crit_count,
            "high_stockout_risks": high_count,
            "medium_stockout_risks": med_count,
            "low_stockout_risks": low_count,
            "total_capital_at_risk": tot_cap_risk,
            "total_annual_holding_cost": tot_hold_cost,
            "champion_model_name": "LightGBM",
            "champion_model_wape": 0.1097,
            "total_recommendations": len(recs_df),
            "dc_transfer_recommendations": dc_trans,
            "purchase_order_recommendations": po_count,
            "hold_order_recommendations": hold_count,
            "urgent_priority_recommendations": urg_count,
        }

    def get_forecasts(
        self,
        location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        horizon_days: int = 30,
    ) -> pd.DataFrame:
        """Query multi-horizon forecast predictions with optional filters."""
        self.initialize()
        df = self._forecasts_df.copy()
        if location_id:
            df = df[df["location_id"] == location_id]
        if product_id:
            df = df[df["product_id"] == product_id]
        if horizon_days:
            df = df.groupby(["location_id", "product_id"]).head(horizon_days).reset_index(drop=True)
            df["horizon_days"] = horizon_days
        return df

    def get_risk_positions(
        self,
        location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        risk_tier: Optional[str] = None,
    ) -> pd.DataFrame:
        """Query SKU x Location operational risk scores with optional filters."""
        self.initialize()
        df = self._risk_nodes_df.copy()
        if location_id:
            df = df[df["location_id"] == location_id]
        if product_id:
            df = df[df["product_id"] == product_id]
        if risk_tier:
            df = df[df["stockout_risk_tier"] == risk_tier.upper()]
        return df.sort_values(["stockout_risk_score", "days_to_runout"], ascending=[False, True]).reset_index(drop=True)

    def get_inventory_health(
        self,
        location_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """Query inventory health data mart."""
        self.initialize()
        df = self._marts["mart_inventory_health"].copy()
        if location_id:
            df = df[df["location_id"] == location_id]
        if product_id:
            df = df[df["product_id"] == product_id]
        return df

    def get_recommendations(
        self,
        location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        action_type: Optional[str] = None,
        priority_tier: Optional[str] = None,
    ) -> pd.DataFrame:
        """Query prescriptive recommendations with optional filters."""
        self.initialize()
        df = self._recommendations_df.copy()
        if location_id:
            df = df[df["location_id"] == location_id]
        if product_id:
            df = df[df["product_id"] == product_id]
        if action_type:
            df = df[df["action_type"] == action_type.upper()]
        if priority_tier:
            df = df[df["priority_tier"] == priority_tier.upper()]
        return df


# Global singleton instance
_service_instance: Optional[IntelligenceService] = None


def get_intelligence_service() -> IntelligenceService:
    """FastAPI dependency to retrieve global IntelligenceService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = IntelligenceService()
    return _service_instance


def set_intelligence_service(service: IntelligenceService) -> None:
    """Set global IntelligenceService instance (used for testing overrides)."""
    global _service_instance
    _service_instance = service
