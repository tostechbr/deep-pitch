"""Tools do agente.

Por ora o baseline estatístico; nas próximas etapas entram busca web e feed
ao vivo (football-data.org).
"""

from .baseline import BaselineResult, baseline_prediction, head_to_head, predict_match
from .feed import live_feed
from .reconcile import Adjustment, apply_adjustments, reconcile
from .search import web_search

__all__ = [
    "BaselineResult",
    "baseline_prediction",
    "head_to_head",
    "predict_match",
    "live_feed",
    "web_search",
    "reconcile",
    "apply_adjustments",
    "Adjustment",
]
