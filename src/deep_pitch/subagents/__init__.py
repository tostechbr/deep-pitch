"""Subagents do deep-pitch: scout (ao vivo) + historian (estatística)."""

from .historian import historian_subagent
from .scout import scout_subagent

__all__ = ["scout_subagent", "historian_subagent"]
