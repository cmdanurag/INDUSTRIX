"""
schemas/common.py
=================
Shared Pydantic types used across multiple schema modules.
"""
from typing import List
from pydantic import BaseModel, Field, validator


class QualityArray(BaseModel):
    """A validated 101-integer quality array."""
    data: List[int] = Field(..., min_length=101, max_length=101)

    @validator("data", each_item=True)
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Quality array values must be non-negative.")
        return v


class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""


class PhaseStatusResponse(BaseModel):
    """Returned by the public polling endpoint GET /status."""
    game_name:    str
    cycle_number: int
    phase:        str
    game_active:  bool