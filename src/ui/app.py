"""Streamlit Enterprise Decision Intelligence Dashboard.

Provides an interactive planner decision surface across 5 core views:
1. Executive Overview: Network KPIs, stockout risk distribution, and urgent actions.
2. Forecast Explorer: Multi-horizon LightGBM forecasts vs actual unconstrained demand.
3. Risk Explorer: 75-node operational risk grid, severity scores, and root causes.
4. Recommendation Center: Prescriptive POs, DC lateral transfers, and explainable audit trails.
5. Inventory / SKU Drill-Down: Daily simulation trajectory, buffer erosion, and safety stock parameters.
"""

from datetime import date
import pandas as pd
import streamlit as st

from src.api.service import get_intelligence_service


# Streamlit Page Configuration
st.set_page_config(
    page_title="Demand & Risk Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_cached_service():
    """Cache singleton intelligence service across Streamlit user sessions."""
    service = get_intelligence_service()
    service.initialize()
    return service


def render_header(summary: dict):
    """Render top banner with system status and analysis date."""
    st.title("⚡ Real-Time Demand & Risk Intelligence Engine")
    st.caption(
        f"**Enterprise Decision Support System** | Reference As-Of Date: `{summary['as_of_date']}` | "
        f"Champion Model: `{summary['champion_model_name']}` (Holdout WAPE: `{summary['champion_model_wape']*100:.2f}%`)"
    )
    st.markdown("---")


def render_executive_overview(service, summary: dict):
    """Render Executive Overview tab."""
    st.subheader("Executive Overview & Network Risk Profile")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Active Node Positions", f"{summary['total_node_positions']}", help="5 Facilities x 15 Catalog SKUs")
    col2.metric("Critical Stockout Risks", f"{summary['critical_stockout_risks']}", delta=f"-{summary['critical_stockout_risks']} Actions Req", delta_color="inverse")
    col3.metric("Excess Capital at Risk", f"${summary['total_capital_at_risk']:,.2f}", help="Excess stock over 45-day target buffer")
    col4.metric("Annual Holding Cost Drag", f"${summary['total_annual_holding_cost']:,.2f}", help="20% annual holding cost on excess capital")
    col5.metric("Open Prescriptive Actions", f"{summary['total_recommendations']}", f"{summary['urgent_priority_recommendations']} Urgent", delta_color="inverse")

    st.markdown("###")

    left_col, right_col = st.columns([1, 1])
    with left_col:
        st.markdown("#### 🚨 Stockout Severity Breakdown")
        risk_dist = pd.DataFrame({
            "Risk Tier": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            "Node Positions": [
                summary["critical_stockout_risks"],
                summary["high_stockout_risks"],
                summary["medium_stockout_risks"],
                summary["low_stockout_risks"],
            ]
        }).set_index("Risk Tier")
        st.bar_chart(risk_dist)

    with right_col:
        st.markdown("#### 📋 Action Type Breakdown")
        action_dist = pd.DataFrame({
            "Action Type": ["DC Lateral Transfer", "Supplier Purchase Order", "Excess Hold / Pause"],
            "Recommended Actions": [
                summary["dc_transfer_recommendations"],
                summary["purchase_order_recommendations"],
                summary["hold_order_recommendations"],
            ]
        }).set_index("Action Type")
        st.bar_chart(action_dist)

    st.markdown("### ⚡ Top Urgent Action Items")
    recs_df = service.get_recommendations(priority_tier="URGENT")
    if len(recs_df) > 0:
        display_cols = [
            "recommendation_id", "location_name", "product_name", "abc_xyz_segment",
            "action_type", "recommended_qty", "days_to_runout", "root_cause", "rationale_text"
        ]
        st.dataframe(recs_df[display_cols].head(10), use_container_width=True)

        # CSV Download Button
        csv_data = recs_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Urgent Action Items (CSV)",
            data=csv_data,
            file_name=f"urgent_actions_{summary['as_of_date']}.csv",
            mime="text/csv",
        )
    else:
        st.success("No urgent stockout actions pending.")


def render_forecast_explorer(service):
    """Render Forecast Explorer tab."""
    st.subheader("Multi-Horizon Demand Forecast Explorer")
    st.markdown("Interactive comparison of champion **LightGBM** forecasts against true unconstrained customer demand.")

    raw_forecasts = service.get_forecasts()
    locations = sorted(raw_forecasts["location_id"].unique())
    products = sorted(raw_forecasts["product_id"].unique())

    col1, col2, col3 = st.columns(3)
    sel_loc = col1.selectbox("Select Facility", locations, index=0)
    sel_prod = col2.selectbox("Select Product SKU", products, index=0)
    sel_horizon = col3.slider("Forecast Horizon (Days)", min_value=7, max_value=30, value=30, step=1)

    node_fc = service.get_forecasts(location_id=sel_loc, product_id=sel_prod, horizon_days=sel_horizon)

    if len(node_fc) > 0:
        chart_df = node_fc[["transaction_date", "y_true", "y_pred"]].copy()
        chart_df = chart_df.rename(columns={"y_true": "True Demand (Actual)", "y_pred": "LightGBM Forecast"}).set_index("transaction_date")
        st.line_chart(chart_df)

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        tot_actual = float(node_fc["y_true"].sum())
        tot_pred = float(node_fc["y_pred"].sum())
        wape = round(float(abs(node_fc["y_true"] - node_fc["y_pred"]).sum() / max(1.0, tot_actual)), 4)
        bias = round(float((tot_pred - tot_actual) / max(1.0, tot_actual)), 4)

        metric_col1.metric("Total Actual Demand", f"{tot_actual:.0f} units")
        metric_col2.metric("Total Forecasted Demand", f"{tot_pred:.0f} units")
        metric_col3.metric("Horizon WAPE", f"{wape*100:.2f}%")
        metric_col4.metric("Forecast Bias", f"{bias*100:+.2f}%")

        with st.expander("View Daily Forecast Data Table"):
            st.dataframe(node_fc, use_container_width=True)
    else:
        st.info("No forecast records found for the selected facility and product.")


def render_risk_explorer(service):
    """Render Risk Explorer tab."""
    st.subheader("Predictive Risk & Root-Cause Explorer")
    st.markdown("Real-time risk scoring across all 75 node positions with deterministic causal attribution.")

    all_risks = service.get_risk_positions()

    col1, col2, col3 = st.columns([1, 1, 1])
    tier_filter = col1.multiselect(
        "Filter by Stockout Risk Tier",
        ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    )
    cause_filter = col2.multiselect(
        "Filter by Root Cause",
        all_risks["root_cause"].unique().tolist(),
        default=all_risks["root_cause"].unique().tolist(),
    )
    search_query = col3.text_input("Search SKU or Location", placeholder="e.g. BEV, Manhattan, LOC-ST-01")

    filtered_risks = all_risks[
        (all_risks["stockout_risk_tier"].isin(tier_filter)) &
        (all_risks["root_cause"].isin(cause_filter))
    ]

    if search_query:
        query = search_query.lower()
        filtered_risks = filtered_risks[
            filtered_risks["product_name"].str.lower().str.contains(query) |
            filtered_risks["location_name"].str.lower().str.contains(query) |
            filtered_risks["sku"].str.lower().str.contains(query) |
            filtered_risks["location_id"].str.lower().str.contains(query)
        ]

    st.markdown(f"**Showing {len(filtered_risks)} of {len(all_risks)} node positions**")

    if len(filtered_risks) > 0:
        display_cols = [
            "location_name", "product_name", "abc_xyz_segment", "stockout_risk_tier",
            "stockout_risk_score", "days_to_runout", "starting_available_stock",
            "safety_stock", "reorder_point", "is_excess", "capital_at_risk",
            "root_cause", "root_cause_explanation"
        ]
        st.dataframe(filtered_risks[display_cols], use_container_width=True)
    else:
        st.warning("No node positions match the selected filters or search query.")


def render_recommendation_center(service):
    """Render Recommendation Center tab."""
    st.subheader("Prescriptive Replenishment & Decision Center")
    st.markdown("Actionable, explainable purchase orders and DC lateral transfer recommendations.")

    all_recs = service.get_recommendations()

    col1, col2, col3 = st.columns([1, 1, 1])
    action_filter = col1.multiselect(
        "Filter Action Type",
        all_recs["action_type"].unique().tolist() if len(all_recs) > 0 else [],
        default=all_recs["action_type"].unique().tolist() if len(all_recs) > 0 else [],
    )
    prio_filter = col2.multiselect(
        "Filter Priority Tier",
        ["URGENT", "HIGH", "MEDIUM", "LOW"],
        default=["URGENT", "HIGH", "MEDIUM", "LOW"],
    )
    search_rec = col3.text_input("Search Recommendation", placeholder="e.g. REC-20261231, Coffee, Boston")

    filtered_recs = all_recs[
        (all_recs["action_type"].isin(action_filter)) &
        (all_recs["priority_tier"].isin(prio_filter))
    ]

    if search_rec:
        query = search_rec.lower()
        filtered_recs = filtered_recs[
            filtered_recs["recommendation_id"].str.lower().str.contains(query) |
            filtered_recs["product_name"].str.lower().str.contains(query) |
            filtered_recs["location_name"].str.lower().str.contains(query) |
            filtered_recs["sku"].str.lower().str.contains(query)
        ]

    st.markdown(f"**Showing {len(filtered_recs)} of {len(all_recs)} Action Recommendations**")

    # CSV Export Button for entire recommendation set
    if len(filtered_recs) > 0:
        csv_data = filtered_recs.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered Recommendations (CSV)",
            data=csv_data,
            file_name="prescriptive_recommendations.csv",
            mime="text/csv",
        )
        st.markdown("###")

    if len(filtered_recs) == 0:
        st.warning("No recommendations match the selected filters.")
        return

    for _, rec in filtered_recs.head(20).iterrows():
        with st.container():
            prio_badge = "🔴 URGENT" if rec["priority_tier"] == "URGENT" else ("🟠 HIGH" if rec["priority_tier"] == "HIGH" else "🟡 MEDIUM" if rec["priority_tier"] == "MEDIUM" else "🟢 LOW")
            st.markdown(
                f"#### `{rec['recommendation_id']}` — {prio_badge} : **{rec['action_type']}** for **{rec['product_name']}** at *{rec['location_name']}*"
            )
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Recommended Qty", f"{rec['recommended_qty']} units")
            col_b.metric("Days to Runout", f"{rec['days_to_runout']:.1f} days")
            col_c.metric("Reorder Point (ROP)", f"{rec['reorder_point']:.0f} units")
            col_d.metric("Root Cause", f"{rec['root_cause']}")
            st.info(f"**Rationale:** {rec['rationale_text']}")
            st.markdown("---")


def render_sku_drilldown(service):
    """Render SKU & Facility Drilldown tab."""
    st.subheader("SKU & Facility Daily Inventory Trajectory Drill-Down")
    st.markdown("Detailed step-by-step balance simulation showing buffer erosion and reorder timing.")

    all_risks = service.get_risk_positions()
    locations = sorted(all_risks["location_id"].unique())
    products = sorted(all_risks["product_id"].unique())

    col1, col2 = st.columns(2)
    sel_loc = col1.selectbox("Facility", locations, index=0, key="drill_loc")
    sel_prod = col2.selectbox("Product SKU", products, index=0, key="drill_prod")

    matching = all_risks[(all_risks["location_id"] == sel_loc) & (all_risks["product_id"] == sel_prod)]
    if len(matching) == 0:
        st.warning("No inventory data found for the selected node.")
        return

    node_risk = matching.iloc[0]

    st.markdown(f"### Position: **{node_risk['product_name']}** @ *{node_risk['location_name']}* (`{node_risk['abc_xyz_segment']}`)")

    colA, colB, colC, colD = st.columns(4)
    colA.metric("Starting Available Stock", f"{node_risk['starting_available_stock']:.0f} units")
    colB.metric("Days to Runout", f"{node_risk['days_to_runout']:.1f} days", help=f"Horizon category: {node_risk['runout_horizon_category']}")
    colC.metric("Safety Stock (SS)", f"{node_risk['safety_stock']:.1f} units")
    colD.metric("Reorder Point (ROP)", f"{node_risk['reorder_point']:.1f} units")

    st.markdown("#### Operational Diagnosis")
    st.warning(f"**Root Cause: `{node_risk['root_cause']}`** — {node_risk['root_cause_explanation']}")


def main():
    """Main Streamlit dashboard application."""
    service = load_cached_service()
    summary = service.get_executive_summary()

    render_header(summary)

    tabs = st.tabs([
        "📊 Executive Overview",
        "📈 Forecast Explorer",
        "🚨 Risk Explorer",
        "📋 Recommendation Center",
        "🔍 SKU Drill-Down",
    ])

    with tabs[0]:
        render_executive_overview(service, summary)
    with tabs[1]:
        render_forecast_explorer(service)
    with tabs[2]:
        render_risk_explorer(service)
    with tabs[3]:
        render_recommendation_center(service)
    with tabs[4]:
        render_sku_drilldown(service)


if __name__ == "__main__":
    main()
