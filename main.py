"""
main.py — AttendX CLI Entry Point
University Attendance Management System

Usage:
    python main.py
    python main.py --seed      (populate demo data)
    python main.py --reset     (delete and reinitialize the database)
"""

import sys
import logging
import argparse
from pathlib import Path

# ─── Logging Setup (must happen before other imports) ─────────────────────────
LOG_PATH = Path("logs")
LOG_PATH.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH / "attendx.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("attendx.main")

# ─── Project imports ──────────────────────────────────────────────────────────
import database as db
import services as svc
import ui
from services import AuthService, StudentService, TeacherService, ModuleService, SessionService, ExportService
from models import Role, AttendanceStatus, SessionStatus


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION SCREENS
# ═══════════════════════════════════════════════════════════════════════════════

def login_screen() -> bool:
    ui.clear()
    ui.show_banner()
    ui.rule("  Sign In  ")
    ui.spacer()

    for attempt in range(3):
        username = ui.prompt_input("Username")
        password = ui.prompt_input("Password", password=True)
        ok, msg = AuthService.login(username, password)
        if ok:
            ui.success(msg)
            ui.wait_key()
            return True
        ui.error(msg)
        if attempt < 2:
            ui.warning(f"{2 - attempt} attempt(s) remaining.")
    ui.error("Too many failed attempts. Exiting.")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def students_menu():
    while True:
        ui.clear()
        ui.header_panel("👨‍🎓  Student Management")
        choice = ui.show_menu("Students", [
            ("1", "📋", "List All Students"),
            ("2", "🔍", "Search Students"),
            ("3", "➕", "Add New Student"),
            ("4", "✏️ ", "Edit Student"),
            ("5", "🗑️ ", "Delete Student"),
            ("6", "📊", "Attendance Report (Student)"),
            ("7", "📚", "Enroll in Module"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            list_students()
        elif choice == "2":
            search_students()
        elif choice == "3":
            add_student()
        elif choice == "4":
            edit_student()
        elif choice == "5":
            delete_student()
        elif choice == "6":
            student_attendance_report()
        elif choice == "7":
            enroll_student_in_module()


def list_students(students=None, title="All Students"):
    if students is None:
        students = db.get_all_students()
    if not students:
        ui.info("No students found.")
        ui.wait_key()
        return

    cols = [
        ("ID",         ui.C["muted"],    "right"),
        ("Code",       ui.C["accent"],   "left"),
        ("Full Name",  ui.C["white"],    "left"),
        ("Department", ui.C["primary"],  "left"),
        ("Year",       ui.C["muted"],    "center"),
        ("Email",      ui.C["muted"],    "left"),
    ]
    for page in ui.paginate(students, page_size=12):
        rows = [[s.id, s.student_id, s.full_name, s.department, s.year_of_study, s.email]
                for s in page]
        ui.print_table(title, cols, rows,
                       caption=f"{len(students)} student(s) total")
    ui.wait_key()


def search_students():
    query = ui.prompt_search("students")
    if not query:
        list_students()
        return
    results = db.search_students(query)
    ui.success(f"{len(results)} result(s) found.")
    list_students(results, f"Search Results: '{query}'")


def add_student():
    ui.section("Add New Student")
    name   = ui.prompt_input("Full Name")
    email  = ui.prompt_input("Email")
    dept   = ui.prompt_input("Department")
    year   = ui.prompt_int("Year of Study", 1, 6)
    phone  = ui.prompt_input("Phone (optional)", default="")
    ok, msg = StudentService.add_student(name, email, dept, year, phone)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def edit_student():
    ui.section("Edit Student")
    students = db.get_all_students()
    list_students(students, "Select Student to Edit")
    sid_input = ui.prompt_input("Enter Student DB ID")
    try:
        sid = int(sid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    student = db.get_student_by_id(sid)
    if not student:
        ui.error("Student not found.")
        ui.wait_key()
        return
    ui.info(f"Editing: {student.full_name}  (leave blank to keep current value)")
    name  = ui.prompt_input("Full Name", default=student.full_name)
    email = ui.prompt_input("Email", default=student.email)
    dept  = ui.prompt_input("Department", default=student.department)
    year  = ui.prompt_int("Year of Study", 1, 6)
    phone = ui.prompt_input("Phone", default=student.phone or "")
    ok, msg = StudentService.edit_student(sid, full_name=name, email=email,
                                          department=dept, year_of_study=year, phone=phone)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def delete_student():
    ui.section("Delete Student")
    students = db.get_all_students()
    list_students(students, "Select Student to Remove")
    sid_input = ui.prompt_input("Enter Student DB ID")
    try:
        sid = int(sid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    student = db.get_student_by_id(sid)
    if not student:
        ui.error("Student not found.")
        ui.wait_key()
        return
    if ui.confirm(f"Deactivate '{student.full_name}'?"):
        ok, msg = StudentService.delete_student(sid)
        (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def student_attendance_report():
    ui.section("Student Attendance Report")
    students = db.get_all_students()
    list_students(students, "Select Student")
    sid_input = ui.prompt_input("Enter Student DB ID")
    try:
        sid = int(sid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    report = StudentService.get_student_attendance_report(sid)
    if not report:
        ui.error("Student not found.")
        ui.wait_key()
        return

    student = report["student"]
    overall = report["overall"]
    ui.spacer()
    ui.console.print(ui.Panel(
        f"[bold {ui.C['white']}]{student.full_name}[/]  [{ui.C['muted']}]({student.student_id})[/]\n"
        f"[{ui.C['muted']}]{student.department} — Year {student.year_of_study}[/]",
        border_style=ui.C["primary"], padding=(0, 2)
    ))

    # Overall bar
    ui.console.print(f"\n  Overall: {ui.attendance_bar(overall['rate'])}")
    ui.console.print(f"  [{ui.C['muted']}]Present: {overall['present']}  |  Late: {overall['late']}  |  Absent: {overall['absent']}  |  Total: {overall['total']}[/]\n")

    # Per-module breakdown
    cols = [
        ("Module", ui.C["accent"], "left"),
        ("Code", ui.C["muted"], "left"),
        ("Total", ui.C["muted"], "center"),
        ("✔ Present", ui.C["present"], "center"),
        ("◑ Late", ui.C["late"], "center"),
        ("✖ Absent", ui.C["absent"], "center"),
        ("Rate", ui.C["white"], "left"),
    ]
    rows = []
    for m in report["modules"]:
        s = m["stats"]
        rows.append([m["name"], m["code"], s["total"],
                     s["present"], s["late"], s["absent"],
                     f"{s['rate']}%"])
    if rows:
        ui.print_table("Per-Module Attendance", cols, rows)
    else:
        ui.info("No module attendance data yet.")
    ui.wait_key()


def enroll_student_in_module():
    ui.section("Enroll Student in Module")
    modules = db.get_all_modules()
    if not modules:
        ui.error("No modules available.")
        ui.wait_key()
        return
    # Display modules
    cols_m = [("ID", ui.C["muted"], "right"), ("Code", ui.C["accent"], "left"), ("Name", ui.C["white"], "left")]
    ui.print_table("Available Modules", cols_m,
                   [[m["id"], m["code"], m["name"]] for m in modules])
    mid_input = ui.prompt_input("Enter Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    # Display students
    students = db.get_all_students()
    list_students(students, "Select Student to Enroll")
    sid_input = ui.prompt_input("Enter Student DB ID")
    try:
        sid = int(sid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    ok, msg = ModuleService.enroll_student(mid, sid)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  TEACHER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def teachers_menu():
    while True:
        ui.clear()
        ui.header_panel("👩‍🏫  Teacher Management")
        choice = ui.show_menu("Teachers", [
            ("1", "📋", "List All Teachers"),
            ("2", "➕", "Add New Teacher"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            list_teachers()
        elif choice == "2":
            add_teacher()


def list_teachers():
    teachers = db.get_all_teachers()
    cols = [
        ("ID",             ui.C["muted"],   "right"),
        ("Code",           ui.C["accent"],  "left"),
        ("Name",           ui.C["white"],   "left"),
        ("Department",     ui.C["primary"], "left"),
        ("Specialization", ui.C["muted"],   "left"),
        ("Email",          ui.C["muted"],   "left"),
    ]
    rows = [[t["id"], t["teacher_code"], t["full_name"],
             t["department"], t["specialization"], t["email"]]
            for t in teachers]
    ui.print_table("All Teachers", cols, rows,
                   caption=f"{len(teachers)} teacher(s)")
    ui.wait_key()


def add_teacher():
    ui.section("Add New Teacher")
    if not AuthService.require_admin():
        ui.error("Admin access required.")
        ui.wait_key()
        return
    name   = ui.prompt_input("Full Name")
    email  = ui.prompt_input("Email")
    uname  = ui.prompt_input("Username")
    pwd    = ui.prompt_input("Password", password=True)
    dept   = ui.prompt_input("Department")
    spec   = ui.prompt_input("Specialization")
    ok, msg = TeacherService.add_teacher(name, email, uname, pwd, dept, spec)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def modules_menu():
    while True:
        ui.clear()
        ui.header_panel("📚  Module Management")
        choice = ui.show_menu("Modules", [
            ("1", "📋", "List All Modules"),
            ("2", "➕", "Add New Module"),
            ("3", "👥", "View Enrolled Students"),
            ("4", "➖", "Unenroll Student"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            list_modules()
        elif choice == "2":
            add_module()
        elif choice == "3":
            view_enrolled()
        elif choice == "4":
            unenroll_student_from_module()


def list_modules():
    modules = db.get_all_modules()
    cols = [
        ("ID",       ui.C["muted"],     "right"),
        ("Code",     ui.C["accent"],    "left"),
        ("Name",     ui.C["white"],     "left"),
        ("Teacher",  ui.C["primary"],   "left"),
        ("Dept",     ui.C["muted"],     "left"),
        ("Credits",  ui.C["muted"],     "center"),
        ("Semester", ui.C["muted"],     "left"),
    ]
    rows = [[m["id"], m["code"], m["name"], m["teacher_name"],
             m["department"], m["credits"], m["semester"]]
            for m in modules]
    ui.print_table("All Modules", cols, rows, caption=f"{len(modules)} module(s)")
    ui.wait_key()


def add_module():
    ui.section("Add New Module")
    teachers = db.get_all_teachers()
    if not teachers:
        ui.error("No teachers found. Add a teacher first.")
        ui.wait_key()
        return
    cols = [("ID", ui.C["muted"], "right"), ("Name", ui.C["white"], "left")]
    ui.print_table("Teachers", cols, [[t["id"], t["full_name"]] for t in teachers])
    tid_input = ui.prompt_input("Assign Teacher (ID)")
    try:
        tid = int(tid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return

    code  = ui.prompt_input("Module Code (e.g. CS301)")
    name  = ui.prompt_input("Module Name")
    desc  = ui.prompt_input("Description")
    dept  = ui.prompt_input("Department")
    cred  = ui.prompt_int("Credits", 1, 10)
    sem   = ui.prompt_input("Semester (e.g. S1-2024)")
    ok, msg = ModuleService.add_module(code, name, desc, tid, dept, cred, sem)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def view_enrolled():
    ui.section("View Enrolled Students")
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Enter Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    students = db.get_enrolled_students(mid)
    list_students(students, "Enrolled Students")


def unenroll_student_from_module():
    ui.section("Unenroll Student from Module")
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Enter Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    students = db.get_enrolled_students(mid)
    list_students(students, "Enrolled Students")
    sid_input = ui.prompt_input("Enter Student DB ID to unenroll")
    try:
        sid = int(sid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    if ui.confirm("Unenroll this student?"):
        ok, msg = ModuleService.unenroll_student(mid, sid)
        (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def list_modules_mini(modules):
    cols = [("ID", ui.C["muted"], "right"), ("Code", ui.C["accent"], "left"), ("Name", ui.C["white"], "left")]
    ui.print_table("Modules", cols, [[m["id"], m["code"], m["name"]] for m in modules])


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def sessions_menu():
    while True:
        ui.clear()
        ui.header_panel("🗓️   Session Management")
        choice = ui.show_menu("Sessions", [
            ("1", "📋", "List Sessions for Module"),
            ("2", "➕", "Create New Session"),
            ("3", "✅", "Mark Attendance"),
            ("4", "👁️ ", "View Session Attendance"),
            ("5", "📰", "Recent Sessions"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            list_sessions_for_module()
        elif choice == "2":
            create_session()
        elif choice == "3":
            mark_attendance()
        elif choice == "4":
            view_session_attendance()
        elif choice == "5":
            recent_sessions()


def list_sessions_for_module():
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Enter Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    sessions = db.get_sessions_by_module(mid)
    cols = [
        ("ID",     ui.C["muted"],    "right"),
        ("Date",   ui.C["accent"],   "left"),
        ("Time",   ui.C["muted"],    "left"),
        ("Room",   ui.C["primary"],  "left"),
        ("Topic",  ui.C["white"],    "left"),
        ("Status", ui.C["muted"],    "left"),
    ]
    rows = [[s.id, s.session_date, f"{s.start_time}–{s.end_time}",
             s.room, s.topic, ui.status_badge(s.status.value)]
            for s in sessions]
    ui.print_table("Sessions", cols, rows, caption=f"{len(sessions)} session(s)")
    ui.wait_key()


def create_session():
    ui.section("Create Session")
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    date_   = ui.prompt_input("Date (YYYY-MM-DD)")
    start   = ui.prompt_input("Start Time (HH:MM)", default="09:00")
    end     = ui.prompt_input("End Time (HH:MM)", default="11:00")
    room    = ui.prompt_input("Room")
    topic   = ui.prompt_input("Topic")
    notes   = ui.prompt_input("Notes (optional)", default="")
    ok, msg = SessionService.create_session(mid, date_, start, end, room, topic, notes)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def mark_attendance():
    ui.section("Mark Attendance")
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return

    sessions = db.get_sessions_by_module(mid)
    scheduled = [s for s in sessions if s.status == SessionStatus.SCHEDULED]
    if not scheduled:
        ui.info("No scheduled sessions for this module.")
        ui.wait_key()
        return

    cols = [("ID", ui.C["muted"], "right"), ("Date", ui.C["accent"], "left"),
            ("Topic", ui.C["white"], "left")]
    ui.print_table("Scheduled Sessions", cols,
                   [[s.id, s.session_date, s.topic] for s in scheduled])
    se_input = ui.prompt_input("Session ID")
    try:
        se_id = int(se_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return

    students = db.get_enrolled_students(mid)
    if not students:
        ui.error("No students enrolled in this module.")
        ui.wait_key()
        return

    ui.spacer()
    ui.rule("  Mark Attendance  |  [P]resent  [A]bsent  [L]ate  ")
    records = []
    for student in students:
        status_input = ui.prompt_choice(
            f"  {student.full_name} ({student.student_id})",
            ["p", "a", "l"]
        )
        status_map = {"p": "present", "a": "absent", "l": "late"}
        records.append({
            "student_id": student.id,
            "status": status_map[status_input],
            "notes": ""
        })

    ok, msg = SessionService.mark_attendance_bulk(se_id, records)
    (ui.success if ok else ui.error)(msg)
    ui.wait_key()


def view_session_attendance():
    ui.section("View Session Attendance")
    se_input = ui.prompt_input("Enter Session ID")
    try:
        se_id = int(se_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    session = db.get_session_by_id(se_id)
    if not session:
        ui.error("Session not found.")
        ui.wait_key()
        return

    records = db.get_attendance_by_session(se_id)
    cols = [
        ("Student Code", ui.C["accent"],   "left"),
        ("Name",         ui.C["white"],    "left"),
        ("Status",       ui.C["muted"],    "left"),
        ("Marked At",    ui.C["muted"],    "left"),
    ]
    rows = [[r["student_code"], r["student_name"],
             ui.status_badge(r["status"]), r["marked_at"][:16]]
            for r in records]
    present = sum(1 for r in records if r["status"] == "present")
    late    = sum(1 for r in records if r["status"] == "late")
    total   = len(records)
    rate    = round(((present + late) / total * 100), 1) if total > 0 else 0.0
    ui.print_table(
        f"Session {se_id} — {session.session_date}  |  {session.topic}",
        cols, rows,
        caption=f"Rate: {rate}%  |  Present: {present}  Late: {late}  Total: {total}"
    )
    ui.wait_key()


def recent_sessions():
    sessions = db.get_recent_sessions(limit=20)
    cols = [
        ("ID",      ui.C["muted"],    "right"),
        ("Date",    ui.C["accent"],   "left"),
        ("Module",  ui.C["white"],    "left"),
        ("Topic",   ui.C["muted"],    "left"),
        ("Room",    ui.C["muted"],    "left"),
        ("Status",  ui.C["muted"],    "left"),
    ]
    rows = [[s["id"], s["session_date"], f"{s['module_code']} — {s['module_name']}",
             s["topic"], s["room"], ui.status_badge(s["status"])]
            for s in sessions]
    ui.print_table("Recent Sessions", cols, rows)
    ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  STATISTICS & REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def statistics_menu():
    while True:
        ui.clear()
        ui.header_panel("📊  Statistics & Reports")
        choice = ui.show_menu("Statistics", [
            ("1", "📉", "Low Attendance Alert (< 75%)"),
            ("2", "📦", "Module Attendance Summary"),
            ("3", "📅", "Weekly Attendance Stats"),
            ("4", "🗂️ ", "Audit Log"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            low_attendance_report()
        elif choice == "2":
            module_attendance_summary()
        elif choice == "3":
            weekly_stats()
        elif choice == "4":
            audit_log()


def low_attendance_report():
    ui.section("Low Attendance Alert")
    threshold_input = ui.prompt_input("Threshold % (default 75)", default="75")
    try:
        threshold = float(threshold_input)
    except ValueError:
        threshold = 75.0

    students = db.get_low_attendance_students(threshold)
    cols = [
        ("Student Code", ui.C["accent"],  "left"),
        ("Name",         ui.C["white"],   "left"),
        ("Department",   ui.C["primary"], "left"),
        ("Sessions",     ui.C["muted"],   "center"),
        ("Attended",     ui.C["muted"],   "center"),
        ("Rate",         ui.C["absent"],  "left"),
    ]
    rows = [[s["student_code"], s["full_name"], s["department"],
             s["total"], s["attended"], ui.attendance_bar(s["rate"], 15)]
            for s in students]
    ui.print_table(
        f"⚠ Students Below {threshold}% Attendance",
        cols, rows,
        caption=f"{len(students)} student(s) flagged"
    )
    ui.wait_key()


def module_attendance_summary():
    ui.section("Module Attendance Summary")
    modules = db.get_all_modules()
    list_modules_mini(modules)
    mid_input = ui.prompt_input("Module ID")
    try:
        mid = int(mid_input)
    except ValueError:
        ui.error("Invalid ID.")
        ui.wait_key()
        return
    m_info = db.get_module_by_id(mid)
    if not m_info:
        ui.error("Module not found.")
        ui.wait_key()
        return
    summary = db.get_module_attendance_summary(mid)
    cols = [
        ("Code",         ui.C["accent"],   "left"),
        ("Name",         ui.C["white"],    "left"),
        ("Total",        ui.C["muted"],    "center"),
        ("✔ Present",   ui.C["present"],  "center"),
        ("◑ Late",      ui.C["late"],     "center"),
        ("✖ Absent",    ui.C["absent"],   "center"),
        ("Rate",         ui.C["white"],    "left"),
    ]
    rows = [[s["student_code"], s["full_name"], s["total"],
             s["present_count"] or 0, s["late_count"] or 0, s["absent_count"] or 0,
             ui.attendance_bar(s["rate"], 12)]
            for s in summary]
    ui.print_table(
        f"Attendance Summary — {m_info['code']}: {m_info['name']}",
        cols, rows,
        caption=f"{len(summary)} student(s)"
    )
    ui.wait_key()


def weekly_stats():
    ui.section("Weekly Attendance Overview")
    stats = db.get_weekly_stats()
    if not stats:
        ui.info("No attendance data yet.")
        ui.wait_key()
        return
    ui.spacer()
    max_total = max(s["total"] for s in stats) or 1
    for s in stats:
        bar_width = int(s["total"] / max_total * 30) if max_total else 0
        bar = "█" * bar_width
        rate = round(s["attended"] / s["total"] * 100, 1) if s["total"] else 0
        color = ui.C["present"] if rate >= 80 else ui.C["late"] if rate >= 60 else ui.C["absent"]
        ui.console.print(
            f"  [bold {ui.C['accent']}]{s['day']:>3}[/]  [{color}]{bar:<30}[/]  "
            f"[{ui.C['muted']}]{s['attended']}/{s['total']}  ({rate}%)[/]"
        )
    ui.spacer()
    ui.wait_key()


def audit_log():
    ui.section("Audit Log")
    logs = db.get_audit_log(limit=50)
    cols = [
        ("Time",    ui.C["muted"],    "left"),
        ("User",    ui.C["accent"],   "left"),
        ("Action",  ui.C["primary"],  "left"),
        ("Details", ui.C["muted"],    "left"),
    ]
    rows = [[l["timestamp"][:16], l["user_name"] or "system",
             l["action"], (l["details"] or "")[:60]]
            for l in logs]
    ui.print_table("System Audit Log (Last 50)", cols, rows)
    ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPORT / BACKUP
# ═══════════════════════════════════════════════════════════════════════════════

def export_menu():
    while True:
        ui.clear()
        ui.header_panel("💾  Export & Backup")
        choice = ui.show_menu("Export", [
            ("1", "📄", "Export Students (CSV)"),
            ("2", "📄", "Export Attendance (CSV)"),
            ("3", "🗃️ ", "Full Export (JSON)"),
            ("4", "🗄️ ", "Backup Database"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            path = ExportService.export_students_csv()
            ui.success(f"Exported → {path}")
        elif choice == "2":
            path = ExportService.export_attendance_csv()
            ui.success(f"Exported → {path}")
        elif choice == "3":
            path = ExportService.export_full_json()
            ui.success(f"Exported → {path}")
        elif choice == "4":
            path = ExportService.backup_database()
            ui.success(f"Backup saved → {path}")
        ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  ACCOUNT SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def account_menu():
    while True:
        ui.clear()
        user = AuthService.current_user()
        ui.header_panel("⚙️   Account Settings", f"{user.full_name} — {user.role.value.upper()}")
        choice = ui.show_menu("Account", [
            ("1", "🔑", "Change Password"),
            ("0", "⬅️ ", "Back"),
        ])
        if choice == "0":
            break
        elif choice == "1":
            old  = ui.prompt_input("Current Password", password=True)
            new1 = ui.prompt_input("New Password", password=True)
            new2 = ui.prompt_input("Confirm New Password", password=True)
            if new1 != new2:
                ui.error("Passwords do not match.")
            else:
                ok, msg = AuthService.change_password(old, new1)
                (ui.success if ok else ui.error)(msg)
            ui.wait_key()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════════

def main_menu():
    user = AuthService.current_user()
    is_admin = AuthService.is_admin()

    while True:
        ui.clear()
        show_dashboard_screen()

        options = [
            ("1", "👨‍🎓", "Student Management"),
            ("2", "📚", "Module Management"),
            ("3", "🗓️ ", "Session Management"),
            ("4", "📊", "Statistics & Reports"),
            ("5", "💾", "Export & Backup"),
        ]
        if is_admin:
            options.insert(1, ("T", "👩‍🏫", "Teacher Management"))

        options += [
            ("A", "⚙️ ", "Account Settings"),
            ("0", "🚪", "Logout"),
        ]

        choice = ui.show_menu("Main Menu", options)

        if choice == "0":
            if ui.confirm("Logout?"):
                AuthService.logout()
                break
        elif choice == "1":
            students_menu()
        elif choice == "T" and is_admin:
            teachers_menu()
        elif choice == "2":
            modules_menu()
        elif choice == "3":
            sessions_menu()
        elif choice == "4":
            statistics_menu()
        elif choice == "5":
            export_menu()
        elif choice == "A":
            account_menu()


def show_dashboard_screen():
    stats = db.get_dashboard_stats()
    user = AuthService.current_user()
    ui.show_dashboard(stats, user.full_name, user.role.value)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AttendX — University Attendance Management")
    parser.add_argument("--seed",  action="store_true", help="Seed demo data")
    parser.add_argument("--reset", action="store_true", help="Reset database")
    args = parser.parse_args()

    if args.reset:
        import os
        if Path(db.DB_PATH).exists():
            os.remove(db.DB_PATH)
        ui.console.print("[bold red]Database reset.[/]")

    db.initialize_database()

    if args.seed:
        svc.seed_demo_data()
        ui.console.print("[bold green]Demo data seeded. Default login: admin / admin123[/]")
        sys.exit(0)

    # Auto-seed if empty
    with db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        svc.seed_demo_data()
        logger.info("Auto-seeded demo data.")

    # Main application loop
    while True:
        if not login_screen():
            break
        main_menu()
        ui.clear()
        ui.show_banner()
        ui.console.print(f"  [{ui.C['secondary']}]You have been logged out. Goodbye![/]\n")
        again = ui.confirm("Login again?")
        if not again:
            break

    logger.info("AttendX CLI exited.")


if __name__ == "__main__":
    main()
