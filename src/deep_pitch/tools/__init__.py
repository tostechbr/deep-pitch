"""Tools do agente.

Por ora o baseline estatístico; nas próximas etapas entram busca web e feed
ao vivo (football-data.org).
"""

from .baseline import BaselineResult, baseline_prediction, head_to_head, predict_match

__all__ = ["BaselineResult", "baseline_prediction", "head_to_head", "predict_match"]
