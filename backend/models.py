"""Pydantic schemas (DTOs) used across routers."""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------
class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SwitchCompanyInput(BaseModel):
    company_id: str


class ForgotPasswordInput(BaseModel):
    email: EmailStr


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str


# ---------- Companies ----------
class CompanyCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    plan: Optional[str] = "free"
    logo_url: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None


# ---------- Users ----------
Role = Literal["MASTER", "ADMIN", "COMMERCIAL", "ANALYST"]


class UserInvite(BaseModel):
    email: EmailStr
    name: str
    role: Role
    password: str = "changeme123"


class UserRoleUpdate(BaseModel):
    role: Role


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordChangeInput(BaseModel):
    current_password: str
    new_password: str


# ---------- Contacts ----------
ContactType = Literal["lead", "client"]


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: ContactType = "lead"
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    origin: Optional[str] = None
    assigned_to: Optional[str] = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ContactUpdate(BaseModel):
    type: Optional[ContactType] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    origin: Optional[str] = None
    assigned_to: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    score: Optional[int] = None


class TagsInput(BaseModel):
    tags: list[str]


class ActivityCreate(BaseModel):
    type: Literal["call", "email", "whatsapp", "note", "meeting", "task"]
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None


# ---------- Pipelines ----------
class PipelineCreate(BaseModel):
    name: str
    is_default: bool = False


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None


class StageCreate(BaseModel):
    name: str
    position: int = 0
    conversion_probability: float = 0.5
    color: str = "#3b82f6"
    sla_hours: int = 72


class StageUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None
    conversion_probability: Optional[float] = None
    color: Optional[str] = None
    sla_hours: Optional[int] = None


class StageReorderItem(BaseModel):
    id: str
    position: int


# ---------- Deals ----------
class DealCreate(BaseModel):
    contact_id: str
    pipeline_id: str
    stage_id: str
    title: str
    value: float = 0
    expected_close_date: Optional[str] = None  # ISO date
    assigned_to: Optional[str] = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class DealUpdate(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    expected_close_date: Optional[str] = None
    assigned_to: Optional[str] = None
    stage_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None


class StageMoveInput(BaseModel):
    stage_id: str
    pipeline_id: Optional[str] = None


class LostInput(BaseModel):
    reason: str


# ---------- Tasks ----------
TaskStatus = Literal["pending", "done", "overdue"]
TaskPriority = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    priority: TaskPriority = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
