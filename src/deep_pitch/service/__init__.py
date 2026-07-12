"""Camada de serviço: orquestração transport-agnostic."""

from .predict import StreamEvent, run_prediction, stream_prediction

__all__ = ["run_prediction", "stream_prediction", "StreamEvent"]
