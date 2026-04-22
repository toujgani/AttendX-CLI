"""
database.py — SQLite persistence layer for AttendX CLI
Handles all DB initialization, CRUD operations, and queries.
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from models import (
    User, Student, Teacher, Module, Session, Attendance,
    ModuleEnrollment, Role, AttendanceStatus, SessionStatus
)

logger = logging.getLogger("attendx.database")

DB_PATH = Path("attendx.db")


# ─── Connection Management ────────────────────────────────────────────────────

@contextmanager
def get_connection():
    """Context manager for safe SQLite connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Schema Setup ─────────────────────────────────────────────────────────────

def initialize_database():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password_hash TEXT  NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('admin','teacher')),
                full_name   TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                created_at  TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS students (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   TEXT    NOT NULL UNIQUE,
                full_name    TEXT    NOT NULL,
                email        TEXT    NOT NULL UNIQUE,
                department   TEXT    NOT NULL,
                year_of_study INTEGER NOT NULL,
                phone        TEXT,
                created_at   TEXT    NOT NULL,
                is_active    INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS teachers (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id),
                teacher_code   TEXT    NOT NULL UNIQUE,
                department     TEXT    NOT NULL,
                specialization TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS modules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT    NOT NULL UNIQUE,
                name        TEXT    NOT NULL,
                description TEXT,
                teacher_id  INTEGER NOT NULL REFERENCES teachers(id),
                department  TEXT    NOT NULL,
                credits     INTEGER NOT NULL DEFAULT 3,
                semester    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id    INTEGER NOT NULL REFERENCES modules(id),
                session_date TEXT    NOT NULL,
                start_time   TEXT    NOT NULL,
                end_time     TEXT    NOT NULL,
                room         TEXT    NOT NULL,
                topic        TEXT    NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'scheduled',
                notes        TEXT
            );

            CREATE TABLE IF NOT EXISTS attendances (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                student_id INTEGER NOT NULL REFERENCES students(id),
                status     TEXT    NOT NULL CHECK(status IN ('present','absent','late')),
                marked_at  TEXT    NOT NULL,
                notes      TEXT,
                UNIQUE(session_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS module_enrollments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id   INTEGER NOT NULL REFERENCES modules(id),
                student_id  INTEGER NOT NULL REFERENCES students(id),
                enrolled_at TEXT    NOT NULL,
                UNIQUE(module_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL,
                user_id    INTEGER,
                action     TEXT    NOT NULL,
                details    TEXT
            );
        """)
    logger.info("Database initialized.")


# ─── Audit Logging ────────────────────────────────────────────────────────────

def log_action(user_id: Optional[int], action: str, details: str = ""):
    from datetime import datetime
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (timestamp, user_id, action, details) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), user_id, action, details)
        )


# ─── User CRUD ────────────────────────────────────────────────────────────────

def create_user(user: User) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO users (username,password_hash,role,full_name,email,created_at,is_active)
               VALUES (?,?,?,?,?,?,?)""",
            (user.username, user.password_hash, user.role.value,
             user.full_name, user.email, user.created_at, int(user.is_active))
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> Optional[User]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None


def get_all_users() -> List[User]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY full_name").fetchall()
        return [_row_to_user(r) for r in rows]


def update_user(user: User):
    with get_connection() as conn:
        conn.execute(
            """UPDATE users SET full_name=?,email=?,role=?,is_active=? WHERE id=?""",
            (user.full_name, user.email, user.role.value, int(user.is_active), user.id)
        )


def update_user_password(user_id: int, new_hash: str):
    with get_connection() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))


def _row_to_user(row) -> User:
    return User(
        id=row["id"], username=row["username"], password_hash=row["password_hash"],
        role=Role(row["role"]), full_name=row["full_name"], email=row["email"],
        created_at=row["created_at"], is_active=bool(row["is_active"])
    )


# ─── Student CRUD ─────────────────────────────────────────────────────────────

def create_student(s: Student) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO students (student_id,full_name,email,department,year_of_study,phone,created_at,is_active)
               VALUES (?,?,?,?,?,?,?,?)""",
            (s.student_id, s.full_name, s.email, s.department,
             s.year_of_study, s.phone, s.created_at, int(s.is_active))
        )
        return cur.lastrowid


def get_all_students(active_only: bool = True) -> List[Student]:
    with get_connection() as conn:
        q = "SELECT * FROM students"
        if active_only:
            q += " WHERE is_active=1"
        q += " ORDER BY full_name"
        return [_row_to_student(r) for r in conn.execute(q).fetchall()]


def get_student_by_id(student_id: int) -> Optional[Student]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        return _row_to_student(row) if row else None


def search_students(query: str) -> List[Student]:
    with get_connection() as conn:
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM students WHERE is_active=1 AND
               (full_name LIKE ? OR student_id LIKE ? OR email LIKE ? OR department LIKE ?)
               ORDER BY full_name""",
            (like, like, like, like)
        ).fetchall()
        return [_row_to_student(r) for r in rows]


def update_student(s: Student):
    with get_connection() as conn:
        conn.execute(
            """UPDATE students SET full_name=?,email=?,department=?,year_of_study=?,phone=?,is_active=?
               WHERE id=?""",
            (s.full_name, s.email, s.department, s.year_of_study, s.phone, int(s.is_active), s.id)
        )


def delete_student(student_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE students SET is_active=0 WHERE id=?", (student_id,))


def _row_to_student(row) -> Student:
    return Student(
        id=row["id"], student_id=row["student_id"], full_name=row["full_name"],
        email=row["email"], department=row["department"],
        year_of_study=row["year_of_study"], phone=row["phone"],
        created_at=row["created_at"], is_active=bool(row["is_active"])
    )


# ─── Teacher CRUD ─────────────────────────────────────────────────────────────

def create_teacher(t: Teacher) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO teachers (user_id,teacher_code,department,specialization) VALUES (?,?,?,?)",
            (t.user_id, t.teacher_code, t.department, t.specialization)
        )
        return cur.lastrowid


def get_all_teachers() -> List[dict]:
    """Returns teachers joined with their user info."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT t.*, u.full_name, u.email, u.username, u.is_active
            FROM teachers t JOIN users u ON t.user_id = u.id
            ORDER BY u.full_name
        """).fetchall()
        return [dict(r) for r in rows]


def get_teacher_by_user_id(user_id: int) -> Optional[Teacher]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM teachers WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        return Teacher(id=row["id"], user_id=row["user_id"], teacher_code=row["teacher_code"],
                       department=row["department"], specialization=row["specialization"])


def get_teacher_by_id(teacher_id: int) -> Optional[Teacher]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        if not row:
            return None
        return Teacher(id=row["id"], user_id=row["user_id"], teacher_code=row["teacher_code"],
                       department=row["department"], specialization=row["specialization"])


# ─── Module CRUD ──────────────────────────────────────────────────────────────

def create_module(m: Module) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO modules (code,name,description,teacher_id,department,credits,semester,created_at,is_active)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (m.code, m.name, m.description, m.teacher_id, m.department,
             m.credits, m.semester, m.created_at, int(m.is_active))
        )
        return cur.lastrowid


def get_all_modules(active_only: bool = True) -> List[dict]:
    with get_connection() as conn:
        q = """SELECT m.*, u.full_name as teacher_name
               FROM modules m JOIN teachers t ON m.teacher_id=t.id
               JOIN users u ON t.user_id=u.id"""
        if active_only:
            q += " WHERE m.is_active=1"
        q += " ORDER BY m.code"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_module_by_id(module_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT m.*, u.full_name as teacher_name
            FROM modules m JOIN teachers t ON m.teacher_id=t.id
            JOIN users u ON t.user_id=u.id
            WHERE m.id=?
        """, (module_id,)).fetchone()
        return dict(row) if row else None


def get_modules_by_teacher(teacher_id: int) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT m.*, u.full_name as teacher_name
            FROM modules m JOIN teachers t ON m.teacher_id=t.id
            JOIN users u ON t.user_id=u.id
            WHERE m.teacher_id=? AND m.is_active=1
        """, (teacher_id,)).fetchall()
        return [dict(r) for r in rows]


def update_module(m: Module):
    with get_connection() as conn:
        conn.execute(
            """UPDATE modules SET name=?,description=?,department=?,credits=?,semester=?,is_active=?
               WHERE id=?""",
            (m.name, m.description, m.department, m.credits, m.semester, int(m.is_active), m.id)
        )


# ─── Session CRUD ─────────────────────────────────────────────────────────────

def create_session(s: Session) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO sessions (module_id,session_date,start_time,end_time,room,topic,status,notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (s.module_id, s.session_date, s.start_time, s.end_time,
             s.room, s.topic, s.status.value, s.notes)
        )
        return cur.lastrowid


def get_sessions_by_module(module_id: int) -> List[Session]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE module_id=? ORDER BY session_date DESC",
            (module_id,)
        ).fetchall()
        return [_row_to_session(r) for r in rows]


def get_session_by_id(session_id: int) -> Optional[Session]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return _row_to_session(row) if row else None


def get_recent_sessions(limit: int = 10) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.*, m.name as module_name, m.code as module_code, u.full_name as teacher_name
            FROM sessions s
            JOIN modules m ON s.module_id=m.id
            JOIN teachers t ON m.teacher_id=t.id
            JOIN users u ON t.user_id=u.id
            ORDER BY s.session_date DESC, s.start_time DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def update_session_status(session_id: int, status: SessionStatus):
    with get_connection() as conn:
        conn.execute("UPDATE sessions SET status=? WHERE id=?", (status.value, session_id))


def _row_to_session(row) -> Session:
    return Session(
        id=row["id"], module_id=row["module_id"], session_date=row["session_date"],
        start_time=row["start_time"], end_time=row["end_time"], room=row["room"],
        topic=row["topic"], status=SessionStatus(row["status"]), notes=row["notes"]
    )


# ─── Attendance CRUD ──────────────────────────────────────────────────────────

def upsert_attendance(a: Attendance) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO attendances (session_id,student_id,status,marked_at,notes)
               VALUES (?,?,?,?,?)
               ON CONFLICT(session_id,student_id) DO UPDATE SET
               status=excluded.status, marked_at=excluded.marked_at, notes=excluded.notes""",
            (a.session_id, a.student_id, a.status.value, a.marked_at, a.notes)
        )
        return cur.lastrowid


def get_attendance_by_session(session_id: int) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.*, s.full_name as student_name, s.student_id as student_code
            FROM attendances a JOIN students s ON a.student_id=s.id
            WHERE a.session_id=?
            ORDER BY s.full_name
        """, (session_id,)).fetchall()
        return [dict(r) for r in rows]


def get_attendance_by_student(student_id: int) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.*, se.session_date, se.topic, m.name as module_name, m.code as module_code
            FROM attendances a
            JOIN sessions se ON a.session_id=se.id
            JOIN modules m ON se.module_id=m.id
            WHERE a.student_id=?
            ORDER BY se.session_date DESC
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


# ─── Enrollment ───────────────────────────────────────────────────────────────

def enroll_student(module_id: int, student_id: int) -> bool:
    from datetime import datetime
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO module_enrollments (module_id,student_id,enrolled_at) VALUES (?,?,?)",
                (module_id, student_id, datetime.now().isoformat())
            )
        return True
    except sqlite3.IntegrityError:
        return False


def unenroll_student(module_id: int, student_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM module_enrollments WHERE module_id=? AND student_id=?",
            (module_id, student_id)
        )


def get_enrolled_students(module_id: int) -> List[Student]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.* FROM students s
            JOIN module_enrollments e ON s.id=e.student_id
            WHERE e.module_id=? AND s.is_active=1
            ORDER BY s.full_name
        """, (module_id,)).fetchall()
        return [_row_to_student(r) for r in rows]


def get_student_modules(student_id: int) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT m.*, u.full_name as teacher_name
            FROM modules m
            JOIN module_enrollments e ON m.id=e.module_id
            JOIN teachers t ON m.teacher_id=t.id
            JOIN users u ON t.user_id=u.id
            WHERE e.student_id=? AND m.is_active=1
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


# ─── Statistics ───────────────────────────────────────────────────────────────

def get_attendance_stats_for_student(student_id: int, module_id: Optional[int] = None) -> dict:
    """Returns total, present, absent, late counts and rate for a student."""
    with get_connection() as conn:
        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN a.status='absent'  THEN 1 ELSE 0 END) as absent_count,
                SUM(CASE WHEN a.status='late'    THEN 1 ELSE 0 END) as late_count
            FROM attendances a
            JOIN sessions se ON a.session_id=se.id
            WHERE a.student_id=?
        """
        params = [student_id]
        if module_id:
            query += " AND se.module_id=?"
            params.append(module_id)
        row = conn.execute(query, params).fetchone()
        total = row["total"] or 0
        present = row["present_count"] or 0
        late = row["late_count"] or 0
        absent = row["absent_count"] or 0
        rate = round(((present + late) / total * 100), 1) if total > 0 else 0.0
        return {"total": total, "present": present, "late": late, "absent": absent, "rate": rate}


def get_module_attendance_summary(module_id: int) -> List[dict]:
    """Returns per-student attendance summary for a module."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.id, s.student_id as student_code, s.full_name,
                COUNT(a.id) as total,
                SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN a.status='absent'  THEN 1 ELSE 0 END) as absent_count,
                SUM(CASE WHEN a.status='late'    THEN 1 ELSE 0 END) as late_count
            FROM students s
            JOIN module_enrollments e ON s.id=e.student_id
            LEFT JOIN sessions se ON se.module_id=e.module_id
            LEFT JOIN attendances a ON a.student_id=s.id AND a.session_id=se.id
            WHERE e.module_id=? AND s.is_active=1
            GROUP BY s.id
            ORDER BY s.full_name
        """, (module_id,)).fetchall()
        result = []
        for r in rows:
            total = r["total"] or 0
            present = r["present_count"] or 0
            late = r["late_count"] or 0
            rate = round(((present + late) / total * 100), 1) if total > 0 else 0.0
            result.append({**dict(r), "rate": rate})
        return result


def get_low_attendance_students(threshold: float = 75.0) -> List[dict]:
    """Returns students whose overall attendance is below threshold."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.id, s.student_id as student_code, s.full_name, s.department,
                COUNT(a.id) as total,
                SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END) as attended
            FROM students s
            JOIN attendances a ON a.student_id=s.id
            WHERE s.is_active=1
            GROUP BY s.id
            HAVING total > 0
        """).fetchall()
        low = []
        for r in rows:
            rate = round((r["attended"] / r["total"] * 100), 1)
            if rate < threshold:
                low.append({**dict(r), "rate": rate})
        return sorted(low, key=lambda x: x["rate"])


def get_dashboard_stats() -> dict:
    """Returns aggregate counts for the dashboard."""
    with get_connection() as conn:
        students = conn.execute("SELECT COUNT(*) FROM students WHERE is_active=1").fetchone()[0]
        teachers = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
        modules  = conn.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        present  = conn.execute("SELECT COUNT(*) FROM attendances WHERE status='present'").fetchone()[0]
        late     = conn.execute("SELECT COUNT(*) FROM attendances WHERE status='late'").fetchone()[0]
        total_a  = conn.execute("SELECT COUNT(*) FROM attendances").fetchone()[0]
        rate     = round(((present + late) / total_a * 100), 1) if total_a > 0 else 0.0
        return {
            "students": students, "teachers": teachers,
            "modules": modules, "sessions": sessions,
            "attendance_rate": rate, "total_records": total_a
        }


def get_audit_log(limit: int = 50) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT l.*, u.full_name as user_name
            FROM audit_log l LEFT JOIN users u ON l.user_id=u.id
            ORDER BY l.timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_weekly_stats() -> List[dict]:
    """Returns attendance counts grouped by day-of-week."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                strftime('%w', se.session_date) as dow,
                COUNT(a.id) as total,
                SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END) as attended
            FROM attendances a
            JOIN sessions se ON a.session_id=se.id
            GROUP BY dow
            ORDER BY dow
        """).fetchall()
        days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        return [{"day": days[int(r["dow"])], "total": r["total"], "attended": r["attended"]} for r in rows]
