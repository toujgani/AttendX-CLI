# AttendX CLI
### University Attendance Management System

A professional, modular, and feature-rich command-line application for managing student attendance at a university. Built with Python 3.10+, SQLite, and the `rich` library.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app (with demo data auto-seeded)
```bash
python main.py
```

### 3. Login with the default admin account
```
Username: admin
Password: admin123
```

### Other launch options
```bash
# Manually seed demo data then exit
python main.py --seed

# Wipe and reinitialize the database
python main.py --reset
```

---

## 📁 Project Structure

```
attendx_cli/
├── main.py          # CLI entry point — all menus and screen flows
├── models.py        # Dataclasses: User, Student, Teacher, Module, Session, Attendance
├── database.py      # SQLite layer — all CRUD operations and queries
├── services.py      # Business logic — auth, validation, exports, seeding
├── ui.py            # Rich-based UI components (tables, panels, menus, prompts)
├── requirements.txt
├── README.md
├── logs/
│   └── attendx.log  # Auto-created on first run
├── exports/         # Auto-created on first export
│   └── *.csv / *.json / *.db
└── attendx.db       # SQLite database (auto-created)
```

---

## 🎯 Features

### Authentication
- Admin and Teacher roles
- SHA-256 password hashing with random salt
- 3-attempt lockout on login
- Change password from account settings

### Student Management
- Add / Edit / Delete (soft-delete) students
- Auto-generated student IDs (e.g. `STU-2024-0001`)
- Search by name, email, department, or student code
- Per-student attendance reports with module breakdown
- Enroll/unenroll students from modules

### Teacher Management
- Add teachers (creates both User + Teacher profile)
- List all teachers with department and specialization

### Module Management
- Create modules assigned to a teacher
- View enrolled students per module
- Enroll / unenroll students

### Session Management
- Create sessions per module with date, time, room, topic
- Mark attendance: Present / Absent / Late
- View attendance per session
- Recent sessions dashboard

### Statistics & Reports
- 🔴 Low attendance alert — flag students below a threshold
- Module attendance summary (per-student, per-module)
- Weekly attendance bar chart in terminal
- System audit log

### Export & Backup
- Export students → CSV
- Export attendance → CSV
- Full export → JSON
- Database backup → `.db` file

---

## 🎨 UI Design

AttendX uses the `rich` library extensively:
- **Panels** for headers and dashboards
- **Tables** with rounded borders for all data views
- **Colored progress bars** for attendance rates
- **Status badges** (✔ PRESENT, ◑ LATE, ✖ ABSENT)
- **ASCII banner** title screen
- **Paginated** lists for long datasets
- **Consistent color palette**: sky blue, amber, green, red

---

## 🏗️ Architecture

```
main.py          ← Orchestrator: menus, user interaction, screen flow
    │
    ├── services.py   ← Business logic: auth, validation, ID gen, exports
    │       │
    │       └── database.py  ← Pure SQLite CRUD (no business logic)
    │               │
    │               └── models.py  ← Typed dataclasses (no dependencies)
    │
    └── ui.py         ← Rich UI primitives (no business logic)
```

### Key Design Principles
- **OOP** — all entities are typed dataclasses; services are classes with static methods
- **Separation of concerns** — database ↔ services ↔ UI are fully decoupled
- **Soft-delete** — students are deactivated, not removed from the DB
- **Upsert attendance** — re-marking attendance updates in place
- **Audit log** — every write action is logged to `audit_log` table
- **File logging** — all INFO/ERROR events written to `logs/attendx.log`

---

## 👤 Demo Accounts

After seeding, the following accounts are available:

| Username      | Password | Role    | Name               |
|---------------|----------|---------|--------------------|
| admin         | admin123 | Admin   | System Administrator |
| prof.martin   | pass123  | Teacher | Dr. Alice Martin   |
| prof.chen     | pass123  | Teacher | Dr. Bob Chen       |
| prof.dubois   | pass123  | Teacher | Dr. Claire Dubois  |

---

## 📦 Requirements

- Python 3.10+
- `rich >= 13.0.0`
- `sqlite3` (built-in)
- `hashlib`, `secrets`, `csv`, `json`, `shutil`, `logging` (all built-in)

---

## 🔒 Security Notes

- Passwords are never stored in plaintext
- Each password uses a unique 16-byte random salt
- Role-based access: teachers see their modules; admins see everything
- All actions are recorded in the audit log
