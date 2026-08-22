"""Request/response shapes for internship plans."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

InternshipPlanTier = Literal["basic_299", "premium_999"]


class InternshipPlanCreateRequest(BaseModel):
    tier: InternshipPlanTier
    price: int = Field(gt=0, description="Price in whole rupees (e.g. 299, 999)")
    min_duration_weeks: int = Field(gt=0)
    max_duration_weeks: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_duration_range(self) -> InternshipPlanCreateRequest:
        if self.min_duration_weeks > self.max_duration_weeks:
            raise ValueError("min_duration_weeks must be less than or equal to max_duration_weeks")
        return self


class InternshipPlanUpdateRequest(BaseModel):
    tier: InternshipPlanTier | None = None
    price: int | None = Field(default=None, gt=0)
    min_duration_weeks: int | None = Field(default=None, gt=0)
    max_duration_weeks: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> InternshipPlanUpdateRequest:
        fields = (
            self.tier,
            self.price,
            self.min_duration_weeks,
            self.max_duration_weeks,
            self.is_active,
        )
        if all(value is None for value in fields):
            raise ValueError("At least one field must be provided")
        return self


class InternshipPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tier: str
    price: int
    min_duration_weeks: int
    max_duration_weeks: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
