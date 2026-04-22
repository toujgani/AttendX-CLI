"""
services.py — Business logic layer for AttendX CLI
Handles auth, validation, password hashing, exports, and more.
"""

import hashlib
import secrets
import logging
import json
import csv
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Tuple

import database as db
from models import (
    User, Student, Teacher, Module, Session, Attendance,
    Role, AttendanceStatus, SessionStatus
)

logger = logging.getLogger("attendx.services")


# ─── Password Utilities ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """SHA-256 with a random salt, stored as salt:hash."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored salt:hash pair."""
    try:
        salt, h = stored_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


# ─── Authentication ───────────────────────────────────────────────────────────

class AuthService:
    _current_user: Optional[User] = None

    @classmethod
    def login(cls, username: str, password: str) -> Tuple[bool, str]:
        user = db.get_user_by_username(username)
        if not user:
            return False, "User not found."
        if not user.is_active:
            return False, "Account is deactivated."
        if not verify_password(password, user.password_hash):
            return False, "Incorrect password."
        cls._current_user = user
        db.log_action(user.id, "LOGIN", f"User '{username}' logged in.")
        logger.info(f"User '{username}' logged in successfully.")
        return True, f"Welcome, {user.full_name}!"

    @classmethod
    def logout(cls):
        if cls._current_user:
            db.log_action(cls._current_user.id, "LOGOUT", f"User '{cls._current_user.username}' logged out.")
        cls._current_user = None

    @classmethod
    def current_user(cls) -> Optional[User]:
        return cls._current_user

    @classmethod
    def is_admin(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role == Role.ADMIN

    @classmethod
    def is_teacher(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role == Role.TEACHER

    @classmethod
    def require_admin(cls) -> bool:
        return cls.is_admin()

    @classmethod
    def change_password(cls, old_password: str, new_password: str) -> Tuple[bool, str]:
        user = cls._current_user
        if not user:
            return False, "Not logged in."
        if not verify_password(old_password, user.password_hash):
            return False, "Current password is incorrect."
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters."
        db.update_user_password(user.id, hash_password(new_password))
        db.log_action(user.id, "CHANGE_PASSWORD", "Password changed.")
        return True, "Password changed successfully."


# ─── ID Generators ────────────────────────────────────────────────────────────

def generate_student_id() -> str:
    year = datetime.now().year
    students = db.get_all_students(active_only=False)
    count = len(students) + 1
    return f"STU-{year}-{count:04d}"


def generate_teacher_code() -> str:
    teachers = db.get_all_teachers()
    count = len(teachers) + 1
    return f"TCH-{count:03d}"


# ─── Student Service ──────────────────────────────────────────────────────────

class StudentService:

    @staticmethod
    def add_student(full_name: str, email: str, department: str,
                    year_of_study: int, phone: str = "") -> Tuple[bool, str]:
        sid = generate_student_id()
        student = Student(
            id=None, student_id=sid, full_name=full_name.strip(),
            email=email.strip().lower(), department=department.strip(),
            year_of_study=year_of_study, phone=phone.strip() or None
        )
        try:
            new_id = db.create_student(student)
            db.log_action(AuthService.current_user().id, "ADD_STUDENT",
                          f"Added student: {full_name} ({sid})")
            return True, f"Student added successfully with ID: {sid}"
        except Exception as e:
            logger.error(f"Add student failed: {e}")
            return False, f"Failed to add student: {str(e)}"

    @staticmethod
    def edit_student(student_id: int, **kwargs) -> Tuple[bool, str]:
        student = db.get_student_by_id(student_id)
        if not student:
            return False, "Student not found."
        for k, v in kwargs.items():
            if hasattr(student, k) and v is not None:
                setattr(student, k, v)
        try:
            db.update_student(student)
            db.log_action(AuthService.current_user().id, "EDIT_STUDENT",
                          f"Edited student ID {student_id}")
            return True, "Student updated successfully."
        except Exception as e:
            return False, f"Update failed: {str(e)}"

    @staticmethod
    def delete_student(student_id: int) -> Tuple[bool, str]:
        student = db.get_student_by_id(student_id)
        if not student:
            return False, "Student not found."
        db.delete_student(student_id)
        db.log_action(AuthService.current_user().id, "DELETE_STUDENT",
                      f"Deleted student: {student.full_name}")
        return True, f"Student '{student.full_name}' deactivated."

    @staticmethod
    def get_student_attendance_report(student_id: int) -> dict:
        student = db.get_student_by_id(student_id)
        if not student:
            return {}
        modules = db.get_student_modules(student_id)
        module_stats = []
        for m in modules:
            stats = db.get_attendance_stats_for_student(student_id, m["id"])
            module_stats.append({**m, "stats": stats})
        overall = db.get_attendance_stats_for_student(student_id)
        return {
            "student": student,
            "modules": module_stats,
            "overall": overall
        }


# ─── Teacher Service ──────────────────────────────────────────────────────────

class TeacherService:

    @staticmethod
    def add_teacher(full_name: str, email: str, username: str, password: str,
                    department: str, specialization: str) -> Tuple[bool, str]:
        user = User(
            id=None, username=username.strip(), password_hash=hash_password(password),
            role=Role.TEACHER, full_name=full_name.strip(),
            email=email.strip().lower()
        )
        try:
            user_id = db.create_user(user)
            code = generate_teacher_code()
            teacher = Teacher(id=None, user_id=user_id, teacher_code=code,
                              department=department.strip(), specialization=specialization.strip())
            db.create_teacher(teacher)
            db.log_action(AuthService.current_user().id, "ADD_TEACHER",
                          f"Added teacher: {full_name} ({code})")
            return True, f"Teacher added with code: {code}"
        except Exception as e:
            logger.error(f"Add teacher failed: {e}")
            return False, f"Failed: {str(e)}"


# ─── Module Service ───────────────────────────────────────────────────────────

class ModuleService:

    @staticmethod
    def add_module(code: str, name: str, description: str, teacher_id: int,
                   department: str, credits: int, semester: str) -> Tuple[bool, str]:
        module = Module(
            id=None, code=code.strip().upper(), name=name.strip(),
            description=description.strip(), teacher_id=teacher_id,
            department=department.strip(), credits=credits, semester=semester.strip()
        )
        try:
            db.create_module(module)
            db.log_action(AuthService.current_user().id, "ADD_MODULE",
                          f"Added module: {name} ({code})")
            return True, f"Module '{name}' created."
        except Exception as e:
            return False, f"Failed: {str(e)}"

    @staticmethod
    def enroll_student(module_id: int, student_id: int) -> Tuple[bool, str]:
        ok = db.enroll_student(module_id, student_id)
        if ok:
            db.log_action(AuthService.current_user().id, "ENROLL_STUDENT",
                          f"Enrolled student {student_id} in module {module_id}")
            return True, "Student enrolled."
        return False, "Student already enrolled in this module."

    @staticmethod
    def unenroll_student(module_id: int, student_id: int) -> Tuple[bool, str]:
        db.unenroll_student(module_id, student_id)
        return True, "Student unenrolled."


# ─── Session Service ──────────────────────────────────────────────────────────

class SessionService:

    @staticmethod
    def create_session(module_id: int, session_date: str, start_time: str,
                       end_time: str, room: str, topic: str,
                       notes: str = "") -> Tuple[bool, str]:
        s = Session(
            id=None, module_id=module_id, session_date=session_date,
            start_time=start_time, end_time=end_time, room=room.strip(),
            topic=topic.strip(), notes=notes.strip() or None
        )
        try:
            sid = db.create_session(s)
            db.log_action(AuthService.current_user().id, "CREATE_SESSION",
                          f"Session {sid} for module {module_id} on {session_date}")
            return True, f"Session created (ID: {sid})"
        except Exception as e:
            return False, f"Failed: {str(e)}"

    @staticmethod
    def mark_attendance_bulk(session_id: int, records: List[dict]) -> Tuple[bool, str]:
        """
        records = [{"student_id": int, "status": str, "notes": str}, ...]
        """
        try:
            for r in records:
                a = Attendance(
                    id=None, session_id=session_id,
                    student_id=r["student_id"],
                    status=AttendanceStatus(r["status"]),
                    notes=r.get("notes", "")
                )
                db.upsert_attendance(a)
            db.update_session_status(session_id, SessionStatus.COMPLETED)
            db.log_action(AuthService.current_user().id, "MARK_ATTENDANCE",
                          f"Marked attendance for session {session_id}: {len(records)} students")
            return True, f"Attendance marked for {len(records)} students."
        except Exception as e:
            return False, f"Failed: {str(e)}"


# ─── Export Service ───────────────────────────────────────────────────────────

class ExportService:

    EXPORT_DIR = Path("exports")

    @classmethod
    def _ensure_dir(cls):
        cls.EXPORT_DIR.mkdir(exist_ok=True)

    @classmethod
    def export_students_csv(cls) -> str:
        cls._ensure_dir()
        students = db.get_all_students(active_only=False)
        path = cls.EXPORT_DIR / f"students_{_ts()}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["student_id","full_name","email",
                                               "department","year_of_study","phone","created_at"])
            w.writeheader()
            for s in students:
                w.writerow(s.to_dict())
        db.log_action(AuthService.current_user().id, "EXPORT", f"Exported students to {path}")
        return str(path)

    @classmethod
    def export_attendance_csv(cls, module_id: Optional[int] = None) -> str:
        cls._ensure_dir()
        if module_id:
            sessions = db.get_sessions_by_module(module_id)
        else:
            sessions = []
            for m in db.get_all_modules():
                sessions.extend(db.get_sessions_by_module(m["id"]))

        rows = []
        for se in sessions:
            records = db.get_attendance_by_session(se.id)
            for r in records:
                rows.append({
                    "session_id": se.id,
                    "date": se.session_date,
                    "module_id": se.module_id,
                    "student_code": r["student_code"],
                    "student_name": r["student_name"],
                    "status": r["status"],
                    "marked_at": r["marked_at"],
                })
        path = cls.EXPORT_DIR / f"attendance_{_ts()}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader()
                w.writerows(rows)
        db.log_action(AuthService.current_user().id, "EXPORT", f"Exported attendance to {path}")
        return str(path)

    @classmethod
    def export_full_json(cls) -> str:
        cls._ensure_dir()
        data = {
            "exported_at": datetime.now().isoformat(),
            "students": [s.to_dict() for s in db.get_all_students(False)],
            "modules": db.get_all_modules(False),
            "sessions": [],
            "attendance": [],
        }
        for m in db.get_all_modules(False):
            for se in db.get_sessions_by_module(m["id"]):
                data["sessions"].append(se.to_dict())
                for r in db.get_attendance_by_session(se.id):
                    data["attendance"].append(r)
        path = cls.EXPORT_DIR / f"full_export_{_ts()}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        db.log_action(AuthService.current_user().id, "EXPORT", f"Full JSON export to {path}")
        return str(path)

    @classmethod
    def backup_database(cls) -> str:
        cls._ensure_dir()
        backup_path = cls.EXPORT_DIR / f"attendx_backup_{_ts()}.db"
        shutil.copy2(db.DB_PATH, backup_path)
        db.log_action(AuthService.current_user().id, "BACKUP", f"DB backed up to {backup_path}")
        return str(backup_path)


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ─── Seed Data ────────────────────────────────────────────────────────────────

def seed_demo_data():
    """Populate the database with realistic demo data."""
    # Admin user
    admin = User(id=None, username="admin", password_hash=hash_password("admin123"),
                 role=Role.ADMIN, full_name="System Administrator",
                 email="admin@university.edu")
    try:
        db.create_user(admin)
    except Exception:
        return  # already seeded

    # Teacher users
    teachers_data = [
        ("prof.martin", "pass123", "Dr. Alice Martin", "alice.martin@uni.edu",
         "Computer Science", "Algorithms & AI"),
        ("prof.chen", "pass123", "Dr. Bob Chen", "bob.chen@uni.edu",
         "Mathematics", "Linear Algebra"),
        ("prof.dubois", "pass123", "Dr. Claire Dubois", "claire.dubois@uni.edu",
         "Physics", "Quantum Mechanics"),
    ]
    teacher_ids = []
    for uname, pwd, name, email, dept, spec in teachers_data:
        u = User(id=None, username=uname, password_hash=hash_password(pwd),
                 role=Role.TEACHER, full_name=name, email=email)
        uid = db.create_user(u)
        code = generate_teacher_code()
        t = Teacher(id=None, user_id=uid, teacher_code=code, department=dept, specialization=spec)
        tid = db.create_teacher(t)
        teacher_ids.append(tid)

    # Modules
    modules_data = [
        ("CS301", "Data Structures & Algorithms", "Core CS module", teacher_ids[0], "Computer Science", 4, "S1-2024"),
        ("CS402", "Machine Learning", "Introduction to ML", teacher_ids[0], "Computer Science", 3, "S1-2024"),
        ("MA201", "Linear Algebra", "Vectors, matrices", teacher_ids[1], "Mathematics", 3, "S1-2024"),
        ("PH301", "Quantum Physics", "Modern physics", teacher_ids[2], "Physics", 4, "S1-2024"),
    ]
    module_ids = []
    for code, name, desc, tid, dept, cred, sem in modules_data:
        m = Module(id=None, code=code, name=name, description=desc, teacher_id=tid,
                   department=dept, credits=cred, semester=sem)
        mid = db.create_module(m)
        module_ids.append(mid)

    # Students
    students_data = [
        ("Farouk Benali", "farouk.benali@etu.edu", "Computer Science", 3, "+213555001"),
        ("Yacine Hamidi", "yacine.hamidi@etu.edu", "Computer Science", 3, "+213555002"),
        ("Rania Meziane", "rania.meziane@etu.edu", "Computer Science", 2, "+213555003"),
        ("Sofiane Kaci",  "sofiane.kaci@etu.edu",  "Mathematics", 2, "+213555004"),
        ("Amina Cherif",  "amina.cherif@etu.edu",  "Physics", 3, "+213555005"),
        ("Karim Djouadi", "karim.djouadi@etu.edu",  "Computer Science", 1, "+213555006"),
        ("Lina Bouzidi",  "lina.bouzidi@etu.edu",   "Mathematics", 1, "+213555007"),
        ("Omar Boubekeur","omar.boubekeur@etu.edu",  "Physics", 2, "+213555008"),
    ]
    student_ids = []
    for name, email, dept, year, phone in students_data:
        sid_code = generate_student_id()
        s = Student(id=None, student_id=sid_code, full_name=name, email=email,
                    department=dept, year_of_study=year, phone=phone)
        sid = db.create_student(s)
        student_ids.append(sid)

    # Enroll students in modules
    cs_students = student_ids[:4] + [student_ids[5]]
    math_students = [student_ids[3], student_ids[6]]
    phys_students = [student_ids[4], student_ids[7]]

    for mid in module_ids[:2]:
        for sid in cs_students:
            db.enroll_student(mid, sid)
    for sid in math_students:
        db.enroll_student(module_ids[2], sid)
    for sid in phys_students:
        db.enroll_student(module_ids[3], sid)

    # Sessions + Attendance
    import random
    random.seed(42)
    session_dates = ["2024-09-10","2024-09-17","2024-09-24",
                     "2024-10-01","2024-10-08","2024-10-15"]
    statuses = [AttendanceStatus.PRESENT]*7 + [AttendanceStatus.ABSENT]*2 + [AttendanceStatus.LATE]

    for mid, enrolled in [
        (module_ids[0], cs_students),
        (module_ids[2], math_students),
        (module_ids[3], phys_students),
    ]:
        for i, d in enumerate(session_dates[:4]):
            se = Session(id=None, module_id=mid, session_date=d,
                         start_time="09:00", end_time="11:00", room=f"Room-{mid*10+i}",
                         topic=f"Topic {i+1}", status=SessionStatus.COMPLETED)
            se_id = db.create_session(se)
            for sid in enrolled:
                a = Attendance(id=None, session_id=se_id, student_id=sid,
                               status=random.choice(statuses))
                db.upsert_attendance(a)

    logger.info("Demo data seeded successfully.")
