from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    LocationSource,
)


class LocationSnapshotCreate(BaseModel):
    component_id: str
    source: LocationSource
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    recorded_at: Optional[datetime] = None


class LocationSnapshotResponse(BaseModel):
    component_id: str
    source: LocationSource
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(BaseModel):
    alert_type: AlertType
    message: str
    severity: AlertSeverity = AlertSeverity.WARNING
    component_id: Optional[str] = None
    kit_id: Optional[str] = None
    booking_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertResponse(BaseModel):
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    component_id: Optional[str] = None
    kit_id: Optional[str] = None
    booking_id: Optional[str] = None
    message: str
    metadata: dict[str, Any]
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
