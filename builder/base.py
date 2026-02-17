"""Abstract base class for financial model builders."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from builder.outputs import ModelOutput, SensitivityGrid, ValidationIssue


class BaseModelBuilder(ABC):
    """Base interface that all model builders must implement.

    Subclasses provide concrete logic for DCF, comps, operating
    models, or any other valuation methodology.
    """

    @abstractmethod
    def set_assumptions(self, assumptions: Any) -> None:
        """Load a set of assumptions into the builder.

        Parameters
        ----------
        assumptions:
            A Pydantic model (e.g. ``ModelAssumptions``) carrying every
            input the builder needs.
        """

    @abstractmethod
    def build(self) -> ModelOutput:
        """Execute the model and return structured output.

        Returns
        -------
        ModelOutput
            Fully populated projection, terminal-value, and valuation
            summary.
        """

    @abstractmethod
    def validate(self) -> list[ValidationIssue]:
        """Run sanity checks on the most recent build.

        Returns
        -------
        list[ValidationIssue]
            Zero or more warnings / errors.
        """

    @abstractmethod
    def sensitivity_table(
        self,
        param1: str,
        param2: str,
        range1: list[float],
        range2: list[float],
    ) -> SensitivityGrid:
        """Vary two parameters and return an equity-value grid.

        Parameters
        ----------
        param1, param2:
            Assumption field names (e.g. ``"wacc"``, ``"terminal_growth"``).
        range1, range2:
            Discrete values to test for each parameter.

        Returns
        -------
        SensitivityGrid
        """

    @abstractmethod
    def to_markdown(self) -> str:
        """Render the latest build as a formatted Markdown report."""
