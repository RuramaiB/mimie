from sqlalchemy import Column, String, DECIMAL, Integer, Boolean, Date, DateTime, ForeignKey, CLOB, text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class StandORM(Base):
    __tablename__ = "stands"

    stand_number = Column(String(20), primary_key=True)
    location = Column(String(200), nullable=False)
    size_m2 = Column(DECIMAL(12, 2), nullable=False)
    activity = Column(String(50), nullable=False)
    picture_url = Column(String(500), nullable=True)
    gps_coordinates = Column(String(500), nullable=False)  # Treated as text/WKT for multi-db portability
    location_city = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    survey = relationship("StandSurveyORM", back_populates="stand", uselist=False, cascade="all, delete-orphan")
    subdivisions = relationship("StandSubdivisionORM", back_populates="stand", cascade="all, delete-orphan")


class StandSurveyORM(Base):
    __tablename__ = "stand_survey"

    survey_id = Column(Integer, primary_key=True, autoincrement=True)
    stand_number = Column(String(20), ForeignKey("stands.stand_number", ondelete="CASCADE"), nullable=False)
    survey_status = Column(Boolean, default=False, nullable=False)
    province = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stand = relationship("StandORM", back_populates="survey")


class StandSubdivisionORM(Base):
    __tablename__ = "stand_subdivisions"

    subdivision_id = Column(Integer, primary_key=True, autoincrement=True)
    stand_number = Column(String(20), ForeignKey("stands.stand_number", ondelete="RESTRICT"), nullable=False)
    allocation_status = Column(Boolean, default=False, nullable=False)
    size_m2 = Column(DECIMAL(10, 2), nullable=False)
    remarks = Column(String(1000), nullable=True)  # Using String instead of CLOB for compatibility
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stand = relationship("StandORM", back_populates="subdivisions")
    allocations = relationship("StandAllocationORM", back_populates="subdivision")


class StandOwnerORM(Base):
    __tablename__ = "stand_owners"

    stand_owner_id = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    disability_status = Column(Boolean, default=False, nullable=False)
    province = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dependents = relationship("DependentORM", back_populates="owner", cascade="all, delete-orphan")
    allocations = relationship("StandAllocationORM", back_populates="owner")


class DependentORM(Base):
    __tablename__ = "dependents"

    dependent_id = Column(Integer, primary_key=True, autoincrement=True)
    stand_owner_id = Column(Integer, ForeignKey("stand_owners.stand_owner_id", ondelete="CASCADE"), nullable=False)
    firstname = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    disability_status = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("StandOwnerORM", back_populates="dependents")


class StandAllocationORM(Base):
    __tablename__ = "stand_allocations"

    allocation_id = Column(Integer, primary_key=True, autoincrement=True)
    stand_owner_id = Column(Integer, ForeignKey("stand_owners.stand_owner_id", ondelete="RESTRICT"), nullable=False)
    subdivision_id = Column(Integer, ForeignKey("stand_subdivisions.subdivision_id", ondelete="RESTRICT"), nullable=False)
    date_of_allocation = Column(Date, nullable=False)
    price_per_m2 = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("StandOwnerORM", back_populates="allocations")
    subdivision = relationship("StandSubdivisionORM", back_populates="allocations")


class MetadataCatalogueORM(Base):
    __tablename__ = "metadata_catalogue"

    table_name = Column(String(100), primary_key=True)
    column_name = Column(String(100), primary_key=True)
    data_type = Column(String(50), nullable=False)
    is_pii = Column(Boolean, default=False)
    data_classification = Column(String(50), default="Internal")
    data_owner = Column(String(100), default="Ministry of Lands")
    data_steward = Column(String(100), default="GIS Department")
