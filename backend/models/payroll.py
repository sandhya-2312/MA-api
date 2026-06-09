from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class PayrollModule(Base):
    """One monthly attendance & salary sheet (e.g. March 2026)."""

    __tablename__ = "payroll_modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    location = Column(String(200), nullable=True)
    company_name = Column(String(100), nullable=True, default="MC.Engg")

    employees = relationship(
        "PayrollEmployee",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="PayrollEmployee.serial_no",
    )


class PayrollEmployee(Base):
    __tablename__ = "payroll_employees"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("payroll_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    serial_no = Column(Integer, nullable=False, default=1)
    emp_id = Column(String(5), nullable=True)
    name = Column(String(150), nullable=False)
    designation = Column(String(100), nullable=True)
    attendance = Column(JSON, nullable=True)
    ot = Column(String(32), nullable=True)
    advance = Column(Integer, nullable=False, default=0)
    wage = Column(Integer, nullable=False, default=0)
    monthly_salary = Column(Integer, nullable=False, default=0)
    food = Column(Integer, nullable=True)
    remarks = Column(String(100), nullable=True)
    contact_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    project = Column(String(200), nullable=True)
    joining_date = Column(String(20), nullable=True)
    bank_name = Column(String(150), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    upi_id = Column(String(100), nullable=True)
    aadhar_number = Column(String(12), nullable=True)
    pan_number = Column(String(10), nullable=True)

    module = relationship("PayrollModule", back_populates="employees")
