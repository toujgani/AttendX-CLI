"""
models.py — Data models for AttendX CLI
Defines all core entities using dataclasses for clean, typed structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class Role(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ─── Models ───────────────────────────────────────────────────────────────────

@dataclass
class User:
    """Represents a system user (admin or teacher)."""
    id: Optional[int]
    username: str
    password_hash: str
    role: Role
    full_name: str
    email: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role.value,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class Student:
    """Represents a university student."""
    id: Optional[int]
    student_id: str          # e.g. "STU-2024-001"
    full_name: str
    email: str
    department: str
    year_of_study: int
    phone: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "full_name": self.full_name,
            "email": self.email,
            "department": self.department,
            "year_of_study": self.year_of_study,
            "phone": self.phone,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class Teacher:
    """Represents a university teacher/professor."""
    id: Optional[int]
    user_id: int             # FK → users
    teacher_code: str        # e.g. "TCH-001"
    department: str
    specialization: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "teacher_code": self.teacher_code,
            "department": self.department,
            "specialization": self.specialization,
        }


@dataclass
class Module:
    """Represents a university course/module."""
    id: Optional[int]
    code: str                # e.g. "CS301"
    name: str
    description: str
    teacher_id: int          # FK → teachers
    department: str
    credits: int
    semester: str            # e.g. "S1-2024"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "teacher_id": self.teacher_id,
            "department": self.department,
            "credits": self.credits,
            "semester": self.semester,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class Session:
    """Represents a single class session for a module."""
    id: Optional[int]
    module_id: int           # FK → modules
    session_date: str        # ISO date string
    start_time: str          # e.g. "09:00"
    end_time: str            # e.g. "11:00"
    room: str
    topic: str
    status: SessionStatus = SessionStatus.SCHEDULED
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "module_id": self.module_id,
            "session_date": self.session_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "room": self.room,
            "topic": self.topic,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass
class Attendance:
    """Represents an attendance record for one student in one session."""
    id: Optional[int]
    session_id: int          # FK → sessions
    student_id: int          # FK → students
    status: AttendanceStatus
    marked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "status": self.status.value,
            "marked_at": self.marked_at,
            "notes": self.notes,
        }


@dataclass
class ModuleEnrollment:
    """Links students to modules they are enrolled in."""
    id: Optional[int]
    module_id: int
    student_id: int
    enrolled_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "module_id": self.module_id,
            "student_id": self.student_id,
            "enrolled_at": self.enrolled_at,
        }
