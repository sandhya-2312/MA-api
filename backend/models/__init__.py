from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.models.enums import UserRole
from backend.models.payroll import PayrollEmployee, PayrollModule


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
        index=True,
    )
    first_login = Column(Boolean, default=True, nullable=False)
    contact_no = Column(String(64), nullable=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    designation = Column(String(255), nullable=True)
    created_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    projects = relationship("UserProject", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    parameters = Column(JSON, nullable=True)

    users = relationship("UserProject", back_populates="project", cascade="all, delete-orphan")
    data_entries = relationship(
        "ProjectData",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class UserProject(Base):
    __tablename__ = "user_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="projects")
    project = relationship("Project", back_populates="users")


class ProjectData(Base):
    __tablename__ = "project_data"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    meta = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="data_entries")
