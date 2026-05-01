"""Pydantic models for request/response validation."""
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Any
from datetime import datetime


class AnalyseRequest(BaseModel):
    company_name: str
    company_url:  str
    category:     str

    @field_validator("company_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("company_name cannot be empty")
        return v.strip()

    @field_validator("company_url")
    @classmethod
    def url_has_domain(cls, v):
        if "." not in v:
            raise ValueError("company_url must be a valid URL")
        if not v.startswith("http"):
            v = "https://" + v
        return v

    model_config = {"json_schema_extra": {"example": {
        "company_name": "Zepto",
        "company_url":  "https://www.zeptonow.com",
        "category":     "quick commerce grocery delivery",
    }}}


class TrackEventRequest(BaseModel):
    tracking_id: str
    event_type:  str   # "open" | "click" | "reply" | "linkedin_accept" | "meeting"
    touch:       Optional[int] = None
    metadata:    Optional[dict] = None
