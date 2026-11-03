"""A trusted user task. `reference_plan` drives the deterministic mock models only."""

from pydantic import BaseModel, Field

from f2agent.llm.mock import PlannedCall


class Task(BaseModel):
    id: str
    instruction: str                       # the only text real models see as the user turn
    reference_plan: list[PlannedCall] = Field(default_factory=list)
