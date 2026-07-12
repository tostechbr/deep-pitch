"""Tools do agente: baseline Dixon-Coles + head_to_head (histórico), web_search
(notícia/forma), live_feed (football-data.org) e reconcile (determinístico)."""

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
