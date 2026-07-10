"""Synthetic replication package for Clinical-Architectural Debt (CAD)."""

from .config import ExperimentConfig
from .experiment import run_experiment

__all__ = ["ExperimentConfig", "run_experiment"]
__version__ = "0.1.0"
