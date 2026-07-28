"""Consistency report models."""

from typing import Literal

from pydantic import Field

from .blueprint import StrictModel

CheckStatus = Literal["pass", "warning", "fail"]


class CheckResult(StrictModel):
    name: str
    status: CheckStatus
    scope: Literal["core", "execution"] = "core"
    issues: list[str] = Field(default_factory=list)


class ConsistencySummary(StrictModel):
    """Separate core-fact integrity from classroom-execution alignment."""

    core_fact_status: CheckStatus
    execution_alignment_status: CheckStatus
    passed_checks: int = Field(ge=0)
    warning_checks: int = Field(ge=0)
    failed_checks: int = Field(ge=0)


class ConsistencyReport(StrictModel):
    """Structured result of deterministic and optional LLM review."""

    status: CheckStatus
    checks: list[CheckResult]
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: ConsistencySummary | None = None
