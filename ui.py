"""
ui.py — Rich-based terminal UI components for AttendX CLI
Provides reusable panels, tables, prompts, banners, and menus.
"""

import sys
from typing import List, Optional, Any, Callable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.columns import Columns
from rich.rule import Rule
from rich.align import Align
from rich import box
from rich.style import Style
from rich.padding import Padding
from rich.markup import escape

console = Console()

# ─── Color Palette ────────────────────────────────────────────────────────────
C = {
    "primary":   "#4FC3F7",   # sky blue
    "secondary": "#81C784",   # soft green
    "accent":    "#FFB74D",   # amber
    "danger":    "#EF5350",   # red
    "warning":   "#FFF176",   # yellow
    "muted":     "#90A4AE",   # gray-blue
    "bg":        "#1E2A38",   # dark navy (panel bg hint)
    "white":     "bright_white",
    "present":   "#66BB6A",
    "absent":    "#EF5350",
    "late":      "#FFA726",
}


# ─── Banner ───────────────────────────────────────────────────────────────────

ASCII_BANNER = r"""
    _   __  __  ____  _  _  ____  _  _
   / \ (  )(  )(_  _)( \( )( ___)(  \/ )
  / _ \ )(__)(  _)(_  )  (  )__)  )    (
 /_/ \_\____/ (____)(_)\_)(____)  \_/\_/
"""

def show_banner():
    banner_text = Text(ASCII_BANNER, style=f"bold {C['primary']}", justify="center")
    subtitle = Text("  University Attendance Management System  ", style=f"bold {C['accent']}", justify="center")
    version  = Text("  v1.0.0  |  Built with ♥ using Python & Rich  ", style=C["muted"], justify="center")
    console.print()
    console.print(Align.center(banner_text))
    console.print(Align.center(subtitle))
    console.print(Align.center(version))
    console.print()


# ─── Rules & Dividers ─────────────────────────────────────────────────────────

def rule(title: str = "", style: str = C["primary"]):
    console.print(Rule(title, style=style))


def spacer(lines: int = 1):
    for _ in range(lines):
        console.print()


# ─── Notifications ────────────────────────────────────────────────────────────

def success(msg: str):
    console.print(f"  [bold {C['secondary']}]✔  {escape(msg)}[/]")

def error(msg: str):
    console.print(f"  [bold {C['danger']}]✘  {escape(msg)}[/]")

def warning(msg: str):
    console.print(f"  [bold {C['warning']}]⚠  {escape(msg)}[/]")

def info(msg: str):
    console.print(f"  [bold {C['primary']}]ℹ  {escape(msg)}[/]")


# ─── Panels ───────────────────────────────────────────────────────────────────

def header_panel(title: str, subtitle: str = ""):
    content = Text(title, style=f"bold {C['white']}", justify="center")
    if subtitle:
        content.append(f"\n{subtitle}", style=C["muted"])
    console.print(Panel(content, border_style=C["primary"], padding=(1, 4)))


def section(title: str):
    console.print()
    console.print(f"  [bold {C['primary']}]▶  {title}[/]")
    console.print(f"  [dim]{'─' * 50}[/]")


# ─── Menus ────────────────────────────────────────────────────────────────────

def show_menu(title: str, options: List[tuple], back_label: str = "Back") -> str:
    """
    options = [(key, icon, label), ...]
    Returns the chosen key.
    """
    spacer()
    console.print(Panel(
        f"[bold {C['white']}]{title}[/]",
        border_style=C["primary"],
        expand=False,
        padding=(0, 2)
    ))

    for key, icon, label in options:
        console.print(f"   [{C['accent']}]{key}[/]  {icon}  [white]{label}[/]")

    spacer()
    keys = [k for k, _, _ in options]
    choice = Prompt.ask(
        f"  [bold {C['primary']}]Enter your choice[/]",
        choices=keys,
        show_choices=False
    )
    return choice


def confirm(prompt: str) -> bool:
    return Confirm.ask(f"  [bold {C['warning']}]{prompt}[/]")


def prompt_input(label: str, default: str = "", password: bool = False) -> str:
    style = f"[bold {C['primary']}]{label}[/]"
    if password:
        return Prompt.ask(f"  {style}", password=True)
    if default:
        return Prompt.ask(f"  {style}", default=default)
    return Prompt.ask(f"  {style}")


def prompt_int(label: str, min_val: int = 1, max_val: int = 9999) -> int:
    while True:
        raw = Prompt.ask(f"  [bold {C['primary']}]{label}[/]")
        try:
            v = int(raw)
            if min_val <= v <= max_val:
                return v
            warning(f"Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            error("Please enter a valid integer.")


def prompt_choice(label: str, choices: List[str]) -> str:
    return Prompt.ask(
        f"  [bold {C['primary']}]{label}[/]",
        choices=choices,
        show_choices=True
    )


# ─── Tables ───────────────────────────────────────────────────────────────────

def make_table(title: str, columns: List[tuple], rows: List[List[Any]],
               caption: str = "") -> Table:
    """
    columns = [(header, style, justify), ...]
    rows    = list of value lists (matched to columns)
    """
    t = Table(
        title=f"[bold {C['white']}]{title}[/]",
        caption=caption,
        box=box.ROUNDED,
        border_style=C["primary"],
        header_style=f"bold {C['accent']}",
        show_lines=True,
        padding=(0, 1),
    )
    for header, style, justify in columns:
        t.add_column(header, style=style, justify=justify)
    for row in rows:
        t.add_row(*[str(v) if v is not None else "—" for v in row])
    return t


def print_table(title: str, columns: List[tuple], rows: List[List[Any]],
                caption: str = ""):
    if not rows:
        info("No records found.")
        return
    t = make_table(title, columns, rows, caption)
    console.print()
    console.print(t)
    console.print()


# ─── Attendance Status Badge ──────────────────────────────────────────────────

def status_badge(status: str) -> str:
    badges = {
        "present": f"[bold {C['present']}]● PRESENT[/]",
        "absent":  f"[bold {C['absent']}]✖ ABSENT[/]",
        "late":    f"[bold {C['late']}]◑ LATE[/]",
        "scheduled":  f"[{C['primary']}]◌ SCHEDULED[/]",
        "completed":  f"[{C['secondary']}]✔ COMPLETED[/]",
        "cancelled":  f"[{C['muted']}]✕ CANCELLED[/]",
    }
    return badges.get(status.lower(), status)


def attendance_bar(rate: float, width: int = 20) -> str:
    """Renders a coloured ASCII bar for an attendance rate."""
    filled = int(rate / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if rate >= 85:
        color = C["present"]
    elif rate >= 70:
        color = C["late"]
    else:
        color = C["absent"]
    return f"[{color}]{bar}[/] [{color}]{rate:.1f}%[/]"


# ─── Dashboard ────────────────────────────────────────────────────────────────

def show_dashboard(stats: dict, user_name: str, role: str):
    spacer()
    console.print(Panel(
        f"[bold {C['white']}]👋  Welcome back, {user_name}[/]\n"
        f"[{C['muted']}]Role: {role.upper()}   |   AttendX University System[/]",
        border_style=C["primary"],
        padding=(1, 4)
    ))

    cards = [
        Panel(f"[bold {C['primary']}]{stats['students']}[/]\n[{C['muted']}]Students[/]",
              border_style=C["primary"], expand=True),
        Panel(f"[bold {C['secondary']}]{stats['teachers']}[/]\n[{C['muted']}]Teachers[/]",
              border_style=C["secondary"], expand=True),
        Panel(f"[bold {C['accent']}]{stats['modules']}[/]\n[{C['muted']}]Modules[/]",
              border_style=C["accent"], expand=True),
        Panel(f"[bold {C['warning']}]{stats['sessions']}[/]\n[{C['muted']}]Sessions[/]",
              border_style=C["warning"], expand=True),
    ]
    console.print(Columns(cards, expand=True))

    rate = stats["attendance_rate"]
    color = C["present"] if rate >= 85 else C["late"] if rate >= 70 else C["absent"]
    console.print(Panel(
        f"[bold {color}]Overall Attendance Rate:  {rate:.1f}%[/]   "
        f"[{C['muted']}]({stats['total_records']} records)[/]\n"
        f"{attendance_bar(rate, 50)}",
        border_style=color, padding=(0, 2)
    ))
    spacer()


# ─── Pagination ───────────────────────────────────────────────────────────────

def paginate(items: list, page_size: int = 15) -> list:
    """Yields pages of items; user navigates with n/p/q."""
    if not items:
        info("No items to display.")
        return
    total = len(items)
    pages = (total + page_size - 1) // page_size
    page = 0
    while True:
        start = page * page_size
        end   = start + page_size
        yield items[start:end]
        if pages == 1:
            break
        console.print(f"  [{C['muted']}]Page {page+1}/{pages}  |  [bold]n[/]=next  [bold]p[/]=prev  [bold]q[/]=quit[/]")
        choice = Prompt.ask("  Navigate", choices=["n","p","q"], default="q", show_choices=False)
        if choice == "q":
            break
        elif choice == "n" and page < pages - 1:
            page += 1
        elif choice == "p" and page > 0:
            page -= 1


# ─── Progress Spinner ─────────────────────────────────────────────────────────

def with_spinner(label: str, fn: Callable, *args, **kwargs):
    with Progress(
        SpinnerColumn(style=C["primary"]),
        TextColumn(f"[{C['muted']}]{label}[/]"),
        transient=True
    ) as prog:
        prog.add_task(label, total=None)
        return fn(*args, **kwargs)


# ─── Search Filter ────────────────────────────────────────────────────────────

def prompt_search(entity: str = "item") -> str:
    return Prompt.ask(f"  [bold {C['primary']}]Search {entity}[/]  [{C['muted']}](leave blank for all)[/]",
                      default="")


# ─── Select from list ─────────────────────────────────────────────────────────

def select_from_list(items: list, id_field: str, display_fn: Callable,
                     prompt_label: str = "Enter ID") -> Optional[Any]:
    """Asks user to pick an item by its ID field."""
    ids = [str(item[id_field]) if isinstance(item, dict) else str(getattr(item, id_field))
           for item in items]
    if not ids:
        error("No items available.")
        return None
    choice = Prompt.ask(f"  [bold {C['primary']}]{prompt_label}[/]", choices=ids, show_choices=False)
    for item in items:
        val = str(item[id_field]) if isinstance(item, dict) else str(getattr(item, id_field))
        if val == choice:
            return item
    return None


def wait_key(msg: str = "Press Enter to continue..."):
    console.print(f"\n  [{C['muted']}]{msg}[/]")
    input()


def clear():
    console.clear()
