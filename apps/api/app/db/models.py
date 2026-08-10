from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.session import Base


class ThermalSpring(Base):
    __tablename__ = "thermal_springs"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)


class ActiveFault(Base):
    __tablename__ = "active_faults"

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    source = Column(Text)
    geom = Column(Geometry("LINESTRING", srid=4326), nullable=False)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    bbox = Column(Geometry("POLYGON", srid=4326), nullable=False)
    start_date = Column(DateTime(timezone=False), nullable=False)
    end_date = Column(DateTime(timezone=False), nullable=False)
    ndvi_mean = Column(Float)
    lst_anomaly_c = Column(Float)
    fault_proximity_m = Column(Float)
    spring_distance_m = Column(Float)
    score = Column(Float)
    breakdown = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
