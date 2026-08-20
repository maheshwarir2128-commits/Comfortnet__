"""
Additional Pydantic schemas for the honest analytics layer (Phase D).
Kept in a separate module from schemas.py so the original Phase 2 schema
file is not disturbed — an additive change, not a rewrite.
"""
from typing import List, Optional
from pydantic import BaseModel


class NodeHealthOut(BaseModel):
    node_id: str
    health_score: int
    status: str  # healthy | warning | critical
    contributing_factors: List[str]
    method: str = "rule_based_explainable_analytics"
    ai_predictive_maintenance_implemented: bool = False
    note: str = (
        "This is a simple, fully-explainable rule-based score (see app/analytics_rules.py), "
        "not a trained machine-learning model. No predictive-maintenance AI has been built or "
        "validated. No field-trained model exists because no physical ComfortNet node has been deployed."
    )


class NodeAnomaliesOut(BaseModel):
    node_id: str
    anomalies: List[str]
    method: str = "rule_based_trend_comparison"
    note: str = "Explainable prototype analytics — not ML-validated predictive maintenance."
