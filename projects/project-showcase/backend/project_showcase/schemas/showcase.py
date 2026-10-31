"""Response schema for the Project Showcase info endpoint."""

from typing import Literal

from pydantic import BaseModel, Field


class ShowcaseInfo(BaseModel):
    """Identity and load status read from this project's manifest."""

    id: str = Field(description="Manifest id")
    name: str = Field(description="Manifest display name")
    description: str = Field(description="Manifest description")
    status: Literal["ok"]
    message: str
