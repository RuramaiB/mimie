from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
import re

# ═══════════════════════════════════════════════════════
#  SPATIAL GEOMETRY PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════

class GeoJSONPolygon(BaseModel):
    type: str = Field("Polygon", pattern="^Polygon$")
    coordinates: List[List[List[float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_wgs84(cls, v: List[List[List[float]]]) -> List[List[List[float]]]:
        """
        Validates WGS-84 boundaries (longitude -180..180, latitude -90..90).
        """
        for ring in v:
            for pt in ring:
                if len(pt) < 2:
                    raise ValueError("Each GPS coordinate must contain longitude and latitude")
                lng, lat = pt[0], pt[1]
                if not (-180.0 <= lng <= 180.0):
                    raise ValueError(f"Longitude {lng} must be in range -180..180")
                if not (-90.0 <= lat <= 90.0):
                    raise ValueError(f"Latitude {lat} must be in range -90..90")
        return v

# ═══════════════════════════════════════════════════════
#  1. STAND SCHEMAS
# ═══════════════════════════════════════════════════════

class StandBase(BaseModel):
    stand_number: str = Field(..., max_length=20)
    location: str = Field(..., max_length=200)
    size_m2: float = Field(..., gt=0)
    activity: str = Field(..., description="Residential or Commercial")
    picture_url: Optional[str] = Field(None, max_length=500)
    gps_coordinates: Union[str, GeoJSONPolygon] = Field(..., description="WKT string or GeoJSON Polygon")
    location_city: str = Field(..., max_length=100)

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        if v not in ("Residential", "Commercial"):
            raise ValueError("Activity must be either 'Residential' or 'Commercial'")
        return v

    @field_validator("gps_coordinates")
    @classmethod
    def validate_gps_coordinates(cls, v: Union[str, GeoJSONPolygon]) -> Union[str, GeoJSONPolygon]:
        if isinstance(v, str):
            # Basic WKT Polygon verification
            cleaned = v.strip().upper()
            if not (cleaned.startswith("POLYGON") and cleaned.endswith("))")):
                raise ValueError("WKT string must represent a valid POLYGON boundary")
        return v

class StandCreate(StandBase):
    pass

class StandResponse(StandBase):
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  2. SURVEY SCHEMAS
# ═══════════════════════════════════════════════════════

class SurveyBase(BaseModel):
    stand_number: str = Field(..., max_length=20)
    survey_status: bool = Field(False)
    province: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)

class SurveyCreate(SurveyBase):
    pass

class SurveyResponse(SurveyBase):
    survey_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  3. SUBDIVISION SCHEMAS
# ═══════════════════════════════════════════════════════

class SubdivisionBase(BaseModel):
    stand_number: str = Field(..., max_length=20)
    allocation_status: bool = Field(False)
    size_m2: float = Field(..., gt=0)
    remarks: Optional[str] = None

class SubdivisionCreate(SubdivisionBase):
    pass

class SubdivisionResponse(SubdivisionBase):
    subdivision_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  4. DEPENDENTS SCHEMAS
# ═══════════════════════════════════════════════════════

class DependentBase(BaseModel):
    firstname: str = Field(..., max_length=100)
    date_of_birth: date
    gender: str = Field(..., description="Male, Female, or Other")
    disability_status: bool = Field(False)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female", "Other"):
            raise ValueError("Gender must be 'Male', 'Female', or 'Other'")
        return v

class DependentCreate(DependentBase):
    stand_owner_id: int

class DependentResponse(DependentBase):
    dependent_id: int
    stand_owner_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  5. OWNER SCHEMAS
# ═══════════════════════════════════════════════════════

class OwnerBase(BaseModel):
    firstname: str = Field(..., max_length=100)
    date_of_birth: date
    gender: str = Field(..., description="Male, Female, or Other")
    disability_status: bool = Field(False)
    province: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female", "Other"):
            raise ValueError("Gender must be 'Male', 'Female', or 'Other'")
        return v

class OwnerCreate(OwnerBase):
    pass

class OwnerResponse(OwnerBase):
    stand_owner_id: int
    created_at: Optional[datetime] = None
    dependents: List[DependentResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  6. ALLOCATION SCHEMAS
# ═══════════════════════════════════════════════════════

class AllocationBase(BaseModel):
    stand_owner_id: int
    subdivision_id: int
    date_of_allocation: date
    price_per_m2: float = Field(..., gt=0)

class AllocationCreate(BaseModel):
    stand_owner_id: int
    subdivision_id: int
    price_per_m2: float = Field(..., gt=0)

class AllocationResponse(AllocationBase):
    allocation_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  METADATA SCHEMAS
# ═══════════════════════════════════════════════════════

class MetadataBase(BaseModel):
    table_name: str
    column_name: str
    data_type: str
    is_pii: bool
    data_classification: str
    data_owner: str
    data_steward: str

class MetadataResponse(MetadataBase):
    model_config = ConfigDict(from_attributes=True)

# ═══════════════════════════════════════════════════════
#  AUTHENTICATION SCHEMAS
# ═══════════════════════════════════════════════════════

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
