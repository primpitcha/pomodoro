import flet as ft
from flet import (
    Icons as icons, ThemeMode, MainAxisAlignment, CrossAxisAlignment,
    ScrollMode, Ref, Text, Row, Column,
    Container, Stack, ProgressRing, ElevatedButton, TextButton, Card,
    ListView, Icon, Checkbox, ProgressBar, Divider, Switch,
    NavigationBar, NavigationBarDestination, BottomSheet, TextField,
    Page, LinearGradient, TextAlign, ButtonStyle, IconButton, Alignment
)
from datetime import datetime, timedelta, date
import asyncio
import time
import requests


# ==================== Configuration ====================
API_BASE = "http://127.0.0.1:8000"  # ตรวจสอบให้ตรงกับ FastAPI server

# รับ user info จาก argument (json string)
import sys, json
if len(sys.argv) > 1:
    try:
        user_info = json.loads(sys.argv[1])
        USER_ID = user_info.get("id", 1)
        USERNAME = user_info.get("username", "")
        USER_EMAIL = user_info.get("email", "")
    except Exception:
        USER_ID = 1
        USERNAME = ""
        USER_EMAIL = ""
else:
    USER_ID = 1
    USERNAME = ""
    USER_EMAIL = ""

# ==================== Color Palette ====================
PEACH = "#FF8C61"
CORAL = "#E8624A"
AMBER = "#F4A53C"
SAGE = "#8CB87A"
DARK = "#3D2C1E"
MID = "#7A5C44"
SOFT = "#B89880"
BG = "#FFF8F0"
CARD = "#FFFFFF"
PEACH_P = "#FFE8D6"
SAGE_L = "#C8E8BD"
AMBER_P = "#FFF0C2"
PEACH_L = "#FFD6C2"
LINE = "#F0E6E0"
SHADOW = "#F5D2C2"

# ==================== API Functions ====================

def api_get_user(user_id: int) -> dict:
    """ดึงข้อมูลผู้ใช้จาก API"""
    try:
        r = requests.get(f"{API_BASE}/users/{user_id}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] get_user: {e}")
    return None

def api_get_tasks_by_date(user_id: int, date_str: str) -> list:
    """ดึงงานตามวันที่จาก API"""
    try:
        r = requests.get(f"{API_BASE}/tasks/{user_id}/{date_str}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] get_tasks_by_date: {e}")
    return []

def api_get_all_tasks(user_id: int) -> list:
    """ดึงงานทั้งหมดของ user"""
    try:
        r = requests.get(f"{API_BASE}/tasks/all/{user_id}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] get_all_tasks: {e}")
    return []

def api_create_task(user_id: int, title: str, note: str, status: str, date_str: str) -> dict:
    """สร้างงานใหม่ผ่าน API"""
    try:
        payload = {
            "user_id": user_id,
            "title": title,
            "note": note or "",
            "status": status,
            "date": date_str,
        }
        print(f"[DEBUG] Sending POST to {API_BASE}/tasks with payload: {payload}")
        r = requests.post(f"{API_BASE}/tasks", json=payload, timeout=5)
        print(f"[DEBUG] Response status: {r.status_code}, body: {r.text}")
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] create_task: {e}")
    return None

def api_update_task(task_id: int, status: str = None, title: str = None, note: str = None) -> dict:
    """อัปเดตงาน (เช่น เปลี่ยนสถานะ)"""
    try:
        payload = {}
        if status is not None:
            payload["status"] = status
        if title is not None:
            payload["title"] = title
        if note is not None:
            payload["note"] = note
        r = requests.put(f"{API_BASE}/tasks/{task_id}", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] update_task: {e}")
    return None

def api_delete_task(task_id: int) -> bool:
    """ลบงาน"""
    try:
        r = requests.delete(f"{API_BASE}/tasks/{task_id}", timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"[API ERROR] delete_task: {e}")
    return False

def api_create_session(user_id: int, task_id: int, session_type: str,
                       duration_minutes: int, started_at: datetime,
                       ended_at: datetime = None, completed: bool = True) -> dict:
    """บันทึก Pomodoro Session ลง DB"""
    try:
        payload = {
            "user_id": user_id,
            "task_id": task_id,
            "session_type": session_type,
            "duration_minutes": duration_minutes,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat() if ended_at else None,
            "completed": completed,
        }
        r = requests.post(f"{API_BASE}/sessions", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] create_session: {e}")
    return None

def api_get_stats(user_id: int) -> dict:
    """ดึงสถิติรวมของ user"""
    try:
        r = requests.get(f"{API_BASE}/sessions/{user_id}/stats", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[API ERROR] get_stats: {e}")
    return {
        "today_sessions": 0,
        "today_tasks_done": 0,
        "today_focus_hours": 0,
        "total_sessions": 0,
        "total_tasks_done": 0,
        "total_focus_hours": 0,
    }

def api_update_settings(user_id: int, settings: dict) -> bool:
    """อัปเดต settings ของ user"""
    try:
        r = requests.put(f"{API_BASE}/users/{user_id}/settings", json=settings, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"[API ERROR] update_settings: {e}")
    return False

# ==================== In-Memory Cache ====================
# โหลดข้อมูล user จาก API ตอนเริ่ม (หรือใช้ default ถ้า API ไม่ตอบ)
_user_cache = None

def get_user_data() -> dict:
    global _user_cache
    if _user_cache is None:
        data = api_get_user(USER_ID)
        if data:
            _user_cache = {
                "id": data["id"],
                "username": data["username"],
                "email": data["email"],
                "created_at": data["created_at"],
                "work_minutes": data["settings"]["work_minutes"] if data.get("settings") else 25,
                "short_break_minutes": data["settings"]["short_break_minutes"] if data.get("settings") else 5,
                "long_break_minutes": data["settings"]["long_break_minutes"] if data.get("settings") else 15,
                "rounds_before_long_break": data["settings"]["rounds_before_long_break"] if data.get("settings") else 4,
                "selected_music_track": data["settings"]["selected_music_track"] if data.get("settings") else "Lo-Fi Focus Beats",
            }
        else:
            # Fallback ถ้า API ไม่ตอบ
            _user_cache = {
                "id": USER_ID,
                "username": "ผู้ใช้",
                "email": "",
                "created_at": datetime.now().isoformat(),
                "work_minutes": 25,
                "short_break_minutes": 5,
                "long_break_minutes": 15,
                "rounds_before_long_break": 4,
                "selected_music_track": "Lo-Fi Focus Beats",
            }
    return _user_cache

music_tracks = [
    {"id": 1, "name": "Lo-Fi Chill Study", "category": "Lo-Fi Hip Hop", "duration": "5:30", "icon_color": PEACH},
    {"id": 2, "name": "Forest Rain Ambience", "category": "Nature Sounds", "duration": "8:15", "icon_color": SAGE},
    {"id": 3, "name": "Ocean Waves Focus", "category": "Ambient", "duration": "10:00", "icon_color": "#4DA6FF"},
    {"id": 4, "name": "Café Jazz Morning", "category": "Jazz", "duration": "6:45", "icon_color": AMBER},
    {"id": 5, "name": "Deep Sleep Binaural", "category": "Binaural Beats", "duration": "30:00", "icon_color": "#9966FF"},
    {"id": 6, "name": "Deep Work Mode", "category": "Electronic", "duration": "12:20", "icon_color": CORAL},
]

# ==================== Helper Functions ====================
def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_week_dates():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(6)]

def get_thai_day_name(date_obj):
    days_thai = ["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"]
    return days_thai[date_obj.weekday()]

def get_thai_month_name():
    months_thai = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    return months_thai[datetime.now().month]

def get_status_color(status):
    colors = {"todo": PEACH, "in_progress": AMBER, "done": SAGE}
    return colors.get(status, PEACH)

def get_status_text(status):
    texts = {"todo": "📌 ยังไม่เริ่ม", "in_progress": "⚡ กำลังทำ", "done": "✅ เสร็จแล้ว"}
    return texts.get(status, status)

# ==================== SCREEN 1: HOME ====================
def home_screen(page):
    user_data = get_user_data()
    today = get_today_date()

    # ดึงข้อมูลจาก API
    today_tasks = api_get_tasks_by_date(USER_ID, today)
    stats = api_get_stats(USER_ID)

    # Header (No Notification, No Night Mode)
    header = Row(
        [
            Column([
                Text("Pomo Focus", size=22, weight="bold", color=DARK, font_family="Nunito"),
                Text(f"{user_data['username']}", size=14, color=SOFT, font_family="Nunito"),
            ], spacing=2, expand=True),
            Container(
                Text(user_data["username"][0], size=20, color="white", weight="bold"),
                width=44, height=44, bgcolor=CORAL, border_radius=16,
                alignment=ft.alignment.Alignment(0, 0),
            ),
        ],
        alignment=MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=CrossAxisAlignment.CENTER,
    )

    week_dates = get_week_dates()
    date_strip_items = []
    for date_obj in week_dates:
        is_today = date_obj.strftime("%Y-%m-%d") == today
        date_strip_items.append(
            Container(
                Column(
                    [
                        Text(get_thai_day_name(date_obj), size=10, color="white" if is_today else DARK),
                        Text(str(date_obj.day), size=18, weight="bold", color="white" if is_today else DARK),
                    ],
                    spacing=4,
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                ),
                width=44, height=58,
                bgcolor=CORAL if is_today else CARD,
                border_radius=14,
                alignment=ft.alignment.Alignment(0, 0),
            )
        )

    date_strip = Row(date_strip_items, spacing=8, scroll=ScrollMode.AUTO)

    # Total Focus Time (แสดงเฉพาะโฟกัสรวม)
    stats_row = Row([
        Card(Container(Column([
            Text("⏰ โฟกัสรวม", size=12, color=DARK),
            Text(f"{stats['total_focus_hours']}h", size=24, weight="bold", color=AMBER)],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=4,
        ), padding=16)),
    ], spacing=8)

    # งานวันนี้จาก DB (Task View)
    task_cards = []
    for task in today_tasks:
        status_color = get_status_color(task["status"])
        def make_checkbox_change(t_id, current_status):
            def on_change(e):
                new_status = "done" if e.control.value else "todo"
                result = api_update_task(t_id, status=new_status)
                if result:
                    page.controls[0].content = home_screen(page)
                    page.update()
            return on_change
        def on_delete_click(e, tid):
            api_delete_task(tid)
            page.controls[0].content = home_screen(page)
            page.update()
        task_cards.append(
            Container(
                Row([
                    Checkbox(
                        value=task["status"] == "done",
                        on_change=make_checkbox_change(task["id"], task["status"]),
                        check_color=CORAL,
                        active_color=PEACH,
                        shape="round",
                    ),
                    Text(
                        task["title"],
                        size=15,
                        weight="bold",
                        color=SOFT if task["status"] == "done" else DARK,
                        style="lineThrough" if task["status"] == "done" else None,
                        expand=True,
                    ),
                    IconButton(icons.DELETE, icon_color=PEACH, on_click=(lambda tid: (lambda e: on_delete_click(e, tid)))(task["id"])),
                ], spacing=10, alignment=MainAxisAlignment.START),
                padding=12,
                bgcolor=CARD,
                border_radius=16,
                border=ft.Border.all(1, LINE),
                shadow=ft.BoxShadow(blur_radius=8, color=SHADOW, offset=ft.Offset(0,2)),
            )
        )

    task_section = Column(
        [
            Row(
                [
                    Text("งานวันนี้", size=16, weight="bold", color=DARK),
                    Text(f"({len(today_tasks)} งาน)", size=12, color="#999"),
                ],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
            ),
            *(task_cards if task_cards else [
                Container(
                    Text("ยังไม่มีงานวันนี้ กด + เพื่อเพิ่มงาน", size=12, color="#999", text_align=TextAlign.CENTER),
                    padding=24,
                    alignment=ft.alignment.Alignment(0, 0),
                )
            ]),
        ],
        spacing=8,
    )

    # Mini Music Card (ดีไซน์คล้าย HTML)
    music_card = Container(
        Row([
            Icon(icons.MUSIC_NOTE, color="white", size=20),
            Column([
                Text(user_data["selected_music_track"] or "เลือกเพลง", size=13, weight="bold", color="white"),
                Text("Lo-Fi Focus Beats", size=10, color="#DDD"),
            ], expand=True, spacing=2),
            IconButton(icons.PLAY_ARROW, icon_color="white", on_click=lambda e: page.go("/music")),
        ], spacing=12, alignment=MainAxisAlignment.CENTER),
        padding=16,
        bgcolor=CORAL,
        border_radius=16,
        shadow=ft.BoxShadow(blur_radius=8, color=SHADOW, offset=ft.Offset(0,2)),
    )

    return ListView(
        [header, date_strip, stats_row, task_section, music_card],
        spacing=16,
        padding=16,
    )

# ==================== SCREEN 2: CALENDAR ====================
def calendar_screen(page, on_day_selected):
    today = datetime.now()

    # ดึงงานทั้งหมดจาก API เพื่อแสดง dots บน calendar
    all_tasks = api_get_all_tasks(USER_ID)

    header = Row(
        [
            TextButton("←", style=ButtonStyle(color=DARK)),
            Column(
                [
                    Text("ปฏิทิน", size=12, color="#999"),
                    Text(f"{get_thai_month_name()} {today.year + 543}", size=18, weight="bold", color=DARK),
                ],
                spacing=2,
            ),
            TextButton("→", style=ButtonStyle(color=DARK)),
        ],
        alignment=MainAxisAlignment.SPACE_BETWEEN,
    )

    dow_header = Row(
        [Text(day, size=12, weight="bold", color=DARK, text_align=TextAlign.CENTER)
         for day in ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"]],
        spacing=4,
    )

    def get_calendar_days():
        first_day = datetime(today.year, today.month, 1)
        last_day = datetime(today.year, today.month + 1 if today.month < 12 else 1, 1) - timedelta(days=1)
        days = []
        for _ in range(first_day.weekday() if first_day.weekday() != 6 else 0):
            days.append(None)
        for day_num in range(1, last_day.day + 1):
            days.append(datetime(today.year, today.month, day_num))
        return days

    calendar_days = get_calendar_days()
    calendar_grid = []

    for day in calendar_days:
        if day is None:
            calendar_grid.append(Container(width=50, height=70))
        else:
            is_today = day.strftime("%Y-%m-%d") == today.strftime("%Y-%m-%d")
            day_str = day.strftime("%Y-%m-%d")
            # กรองจากข้อมูลที่โหลดมาแล้ว
            day_tasks = [t for t in all_tasks if t["date"] == day_str]

            task_dots = []
            for task in day_tasks[:3]:
                task_dots.append(
                    Container(width=6, height=6, bgcolor=get_status_color(task["status"]), border_radius=3)
                )

            day_container = Container(
                Column(
                    [
                        Text(str(day.day), size=14, weight="bold", color="white" if is_today else DARK),
                        Row(task_dots, spacing=2) if task_dots else Container(),
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                width=50, height=70,
                bgcolor=CORAL if is_today else CARD,
                border_radius=12,
                border=ft.border.all(1, PEACH if is_today else "#F0F0F0"),
                on_click=lambda e, d=day: on_day_selected(d),
            )
            calendar_grid.append(day_container)

    grid_rows = []
    for i in range(0, len(calendar_grid), 7):
        grid_rows.append(
            Row(calendar_grid[i:i+7], spacing=4, alignment=MainAxisAlignment.SPACE_BETWEEN)
        )

    # งานที่จะมาถึง (จาก API)
    upcoming_tasks = [
        t for t in all_tasks
        if t["date"] >= today.strftime("%Y-%m-%d")
    ][:3]

    preview_cards = []
    for task in upcoming_tasks:
        preview_cards.append(
            Container(
                Row(
                    [
                        Container(width=4, height=60, bgcolor=get_status_color(task["status"]), border_radius=4),
                        Column(
                            [
                                Text(task["title"], size=12, weight="bold"),
                                Text(task["date"], size=10, color="#999"),
                                Container(
                                    Text(get_status_text(task["status"]), size=9, color="white"),
                                    bgcolor=get_status_color(task["status"]),
                                    padding=ft.padding.symmetric(4, 8),
                                    border_radius=10,
                                ),
                            ],
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=8,
                bgcolor=CARD,
                border_radius=12,
                border=ft.Border.all(1, "#F0F0F0"),
            )
        )

    return ListView(
        [header, Divider(height=20), dow_header, *grid_rows, Divider(height=20),
         Text("งานที่จะมาถึง", size=14, weight="bold", color=DARK),
         *(preview_cards if preview_cards else [Text("ไม่มีงาน", size=12, color="#999")])],
        spacing=8,
        padding=16,
    )

# ==================== SCREEN 3: TIMER ====================
def timer_screen(page, task=None):
    user_data = get_user_data()

    WORK_SECONDS = user_data["work_minutes"] * 60
    SHORT_BREAK = user_data["short_break_minutes"] * 60
    LONG_BREAK = user_data["long_break_minutes"] * 60
    ROUNDS_BEFORE_LONG = user_data["rounds_before_long_break"]

    time_display = Ref[Text]()
    progress_ring = Ref[ProgressRing]()

    current_time = [WORK_SECONDS]
    total_time = [WORK_SECONDS]
    is_running = [False]
    current_round = [1]
    session_type = ["work"]
    session_started_at = [None]
    timer_task = [None]

    def format_time(seconds):
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    time_text = Text(format_time(current_time[0]), size=48, weight="bold", color="white")
    round_text = Text(f"รอบที่ {current_round[0]} จาก {ROUNDS_BEFORE_LONG}", size=12, color="#CCC")
    type_text = Text("⚡ Work", size=13, color=PEACH)
    ring = ProgressRing(value=1.0, width=220, height=220, stroke_width=12, color=PEACH)

    def save_session_to_db(completed: bool):
        """บันทึก session ลง DB"""
        if session_started_at[0]:
            ended = datetime.now()
            elapsed_seconds = WORK_SECONDS - current_time[0] if not completed else WORK_SECONDS
            elapsed_minutes = max(1, elapsed_seconds // 60)
            task_id = task["id"] if task else None
            api_create_session(
                user_id=USER_ID,
                task_id=task_id,
                session_type=session_type[0],
                duration_minutes=elapsed_minutes,
                started_at=session_started_at[0],
                ended_at=ended,
                completed=completed,
            )
            print(f"[SESSION SAVED] type={session_type[0]}, minutes={elapsed_minutes}, completed={completed}")

    async def on_timer_tick():
        while is_running[0] and current_time[0] > 0:
            await asyncio.sleep(1)
            if not is_running[0]:
                break
            current_time[0] -= 1
            time_text.value = format_time(current_time[0])
            ring.value = current_time[0] / total_time[0]
            page.update()
        if is_running[0] and current_time[0] == 0:
            is_running[0] = False
            save_session_to_db(completed=True)
            if session_type[0] == "work" and task and task["status"] == "todo":
                api_update_task(task["id"], status="in_progress")
            time_text.value = "เสร็จ! 🎉"
            page.update()

    def on_play_click(e):
        if not is_running[0]:
            is_running[0] = True
            session_started_at[0] = datetime.now()
            # สั่งงาน async timer
            if timer_task[0] is None or timer_task[0].done():
                timer_task[0] = asyncio.create_task(on_timer_tick())

    def on_reset_click(e):
        if timer_task[0] and not timer_task[0].done():
            is_running[0] = False
        if is_running[0]:
            save_session_to_db(completed=False)
        is_running[0] = False
        current_time[0] = total_time[0]
        time_text.value = format_time(current_time[0])
        ring.value = 1.0
        session_started_at[0] = None
        page.update()

    def switch_session(stype):
        if timer_task[0] and not timer_task[0].done():
            is_running[0] = False
        if is_running[0]:
            save_session_to_db(completed=False)
        is_running[0] = False
        session_started_at[0] = None
        session_type[0] = stype
        if stype == "work":
            total_time[0] = WORK_SECONDS
            ring.color = PEACH
            type_text.value = "⚡ Work"
        elif stype == "short_break":
            total_time[0] = SHORT_BREAK
            ring.color = SAGE
            type_text.value = "☕ พักสั้น"
        else:
            total_time[0] = LONG_BREAK
            ring.color = AMBER
            type_text.value = "🌿 พักยาว"
        current_time[0] = total_time[0]
        time_text.value = format_time(current_time[0])
        ring.value = 1.0
        page.update()

    def on_skip_click(e):
        if timer_task[0] and not timer_task[0].done():
            is_running[0] = False
        if is_running[0]:
            save_session_to_db(completed=False)
        is_running[0] = False
        session_started_at[0] = None
        # ไปรอบถัดไป
        if session_type[0] == "work":
            current_round[0] += 1
            if current_round[0] > ROUNDS_BEFORE_LONG:
                current_round[0] = 1
                switch_session("long_break")
            else:
                switch_session("short_break")
        else:
            switch_session("work")
        round_text.value = f"รอบที่ {current_round[0]} จาก {ROUNDS_BEFORE_LONG}"
        page.update()

    # --- เมนูเลือกโหมดจับเวลา: แสดงสี highlight ที่เมนูที่เลือก ---
    def get_tab_bg(tab):
        if session_type[0] == tab:
            if tab == "work":
                return PEACH
            elif tab == "short_break":
                return SAGE
            else:
                return AMBER
        return "transparent"

    session_tabs = Row(
        [
            Container(
                Text("⚡ Work", size=12, weight="bold"),
                padding=ft.padding.all(12),
                bgcolor=get_tab_bg("work"),
                border_radius=12,
                on_click=lambda e: switch_session("work")
            ),
            Container(
                Text("☕ พักสั้น", size=12, weight="bold"),
                padding=ft.padding.all(12),
                bgcolor=get_tab_bg("short_break"),
                border_radius=12,
                on_click=lambda e: switch_session("short_break")
            ),
            Container(
                Text("🌿 พักยาว", size=12, weight="bold"),
                padding=ft.padding.all(12),
                bgcolor=get_tab_bg("long_break"),
                border_radius=12,
                on_click=lambda e: switch_session("long_break")
            ),
        ],
        spacing=8,
        alignment=MainAxisAlignment.CENTER,
    )

    timer_ring_widget = Container(
        Stack(
            [
                ring,
                Column(
                    [
                        time_text,
                        type_text,
                        round_text,
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
            alignment=ft.alignment.Alignment(0, 0),
        ),
        alignment=ft.alignment.Alignment(0, 0),
    )

    task_info = Container(
        Column(
            [
                Text("งานปัจจุบัน", size=10, color="#CCC", weight="bold"),
                Text(task["title"] if task else "ไม่มีงาน — กลับไปเลือกงานก่อน", size=16, weight="bold", color="white"),
                Text(task.get("note", "") if task else "", size=11, color="#DDD"),
            ],
            spacing=4,
        ),
        padding=16,
        bgcolor="rgba(255, 255, 255, 0.05)",
        border=ft.border.all(1, "rgba(255, 255, 255, 0.2)"),
        border_radius=16,
    )

    controls = Row(
        [
            TextButton("🔄 รีเซ็ต", style=ButtonStyle(color="white"), on_click=on_reset_click),
            ElevatedButton("▶ เริ่มจับเวลา", bgcolor=CORAL, color="white", width=150, height=50, on_click=on_play_click),
            TextButton("⏭ ข้าม", style=ButtonStyle(color="white"), on_click=on_skip_click),
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=12,
    )

    return ListView(
        [
            Row([Text("Pomo Focus", weight="bold", color="white"), IconButton(icons.SETTINGS, icon_color="white")],
                alignment=MainAxisAlignment.SPACE_BETWEEN),
            session_tabs,
            timer_ring_widget,
            task_info,
            controls,
        ],
        spacing=20,
        padding=16,
    )

# ==================== SCREEN 4: MUSIC PLAYER ====================
def music_player_screen(page):
    user_data = get_user_data()

    header = Row(
        [
            Text("เสียงผ่อนคลาย 🎵", size=18, weight="bold", color=DARK),
            IconButton(icons.SEARCH, icon_color=DARK),
        ],
        alignment=MainAxisAlignment.SPACE_BETWEEN,
    )

    hero_card = Container(
        Column(
            [
                Text("กำลังเล่น", size=12, color="#999"),
                Text(user_data["selected_music_track"] or "เลือกเพลง", size=20, weight="bold", color=DARK),
                Text("🍅 เพลงช่วยโฟกัส", size=11, color="#999"),
            ],
            spacing=8,
        ),
        padding=20,
        bgcolor=PEACH_P,
        border_radius=20,
    )

    vinyl = Container(
        Container(
            Text("♫", size=60, color=PEACH, text_align=TextAlign.CENTER),
            width=120, height=120, bgcolor=MID, border_radius=60,
            alignment=ft.alignment.Alignment(0, 0),
        ),
        width=140, height=140, bgcolor=DARK, border_radius=70, padding=10,
        alignment=ft.alignment.Alignment(0, 0),
    )

    now_playing = Container(
        Row(
            [
                vinyl,
                Column(
                    [
                        Text(user_data["selected_music_track"] or "เลือกเพลง", size=14, weight="bold"),
                        Text("Lo-Fi Hip Hop 🎵", size=12, color="#999"),
                    ],
                    spacing=4,
                ),
            ],
            spacing=16,
            vertical_alignment=CrossAxisAlignment.CENTER,
        ),
        padding=16,
        bgcolor=CARD,
        border_radius=16,
        border=ft.Border.all(1, "#F0F0F0"),
    )

    categories = Row(
        [
            Container(Text("🍅 เพลงละครฟังสบาย", size=11, weight="bold", color="white"), bgcolor=PEACH,
                      padding=ft.padding.symmetric(vertical=8, horizontal=12), border_radius=20),
            Container(Text("🌿 เพลงชิลฟีลคาเฟ่", size=11, color=DARK), bgcolor=CARD,
                      padding=ft.padding.symmetric(vertical=8, horizontal=12), border_radius=20,
                      border=ft.Border.all(1, "#F0F0F0")),
        ],
        scroll=ScrollMode.AUTO,
        spacing=8,
    )

    def make_track_click(track_name):
        def on_click(e):
            global _user_cache
            ok = api_update_settings(USER_ID, {"selected_music_track": track_name})
            if ok and _user_cache:
                _user_cache["selected_music_track"] = track_name
            page.controls[0].content = music_player_screen(page)
            page.update()
        return on_click

    track_rows = []
    for track in music_tracks:
        is_selected = track["name"] == (user_data["selected_music_track"] or "")
        track_rows.append(
            Container(
                Row(
                    [
                        Container(
                            Text("▶" if is_selected else str(track["id"]), size=12, weight="bold", color="white"),
                            width=32, height=32, bgcolor=track["icon_color"], border_radius=8,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        Column([
                            Text(track["name"], size=12, weight="bold"),
                            Text(track["category"], size=10, color="#999"),
                        ], expand=True, spacing=2),
                        Text(track["duration"], size=10, color="#999"),
                    ],
                    spacing=12,
                    vertical_alignment=CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor=PEACH_P if is_selected else CARD,
                border_radius=12,
                border=ft.Border.all(1, PEACH if is_selected else "#F0F0F0"),
                on_click=make_track_click(track["name"]),
            )
        )

    return ListView(
        [header, hero_card, now_playing, Divider(height=16),
         Text("หมวดหมู่", size=12, weight="bold", color=DARK), categories,
         Divider(height=16), Text("รายชื่อเพลง", size=12, weight="bold", color=DARK), *track_rows],
        spacing=12,
        padding=16,
    )

# ==================== SCREEN 5: PROFILE ====================
def profile_screen(page):
    user_data = get_user_data()
    stats = api_get_stats(USER_ID)

    hero = Container(
        Column(
            [
                Stack(
                    [
                        Container(Text(user_data["username"][0], size=40, weight="bold", color="white"),
                                  width=80, height=80, bgcolor=CORAL, border_radius=20,
                                  alignment=ft.alignment.Alignment(0, 0)),
                    ],
                    width=80, height=80,
                ),
                Text(user_data["username"], size=18, weight="bold", color=DARK),
                Text(user_data["email"], size=12, color="#999"),
                Text(f"ID: #{user_data['id']}", size=10, color="#999"),
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=20,
        bgcolor=PEACH_P,
        border_radius=20,
        gradient=LinearGradient(begin=Alignment(-1, -1), end=Alignment(1, 1), colors=[PEACH_P, AMBER_P]),
    )

    # สถิติจาก DB จริง
    profile_stats = Row(
        [
            Card(Container(Column([
                Text("🍅 รอบทั้งหมด", size=11, color=DARK),
                Text(str(stats["total_sessions"]), size=20, weight="bold", color=PEACH),
            ], alignment=MainAxisAlignment.CENTER, horizontal_alignment=CrossAxisAlignment.CENTER), padding=12)),
            Card(Container(Column([
                Text("✅ งานทั้งหมด", size=11, color=DARK),
                Text(str(stats["total_tasks_done"]), size=20, weight="bold", color=SAGE),
            ], alignment=MainAxisAlignment.CENTER, horizontal_alignment=CrossAxisAlignment.CENTER), padding=12)),
            Card(Container(Column([
                Text("⏰ โฟกัส", size=11, color=DARK),
                Text(f"{stats['total_focus_hours']}h", size=20, weight="bold", color=AMBER),
            ], alignment=MainAxisAlignment.CENTER, horizontal_alignment=CrossAxisAlignment.CENTER), padding=12)),
        ],
        spacing=8,
    )


    def create_menu_row(icon, title, subtitle):
        return Container(
            Row(
                [
                    Container(Text(icon, size=24), width=40, alignment=ft.alignment.Alignment(0, 0)),
                    Column([Text(title, size=13, weight="bold", color=DARK),
                            Text(subtitle, size=10, color="#999")], expand=True, spacing=2),
                    Text("›", size=20, color=DARK),
                ],
                spacing=12,
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            padding=16,
            bgcolor=CARD,
            border_radius=16,
            border=ft.Border.all(1, "#F0F0F0"),
        )

    logout_btn = Container(
        Row([Text("🚪", size=20), Text("ออกจากระบบ", size=13, weight="bold", color=CORAL, expand=True)], spacing=12),
        padding=16,
        bgcolor="white",
        border=ft.border.all(2, CORAL),
        border_radius=16,
    )

    return ListView(
        [hero, profile_stats, Divider(height=20),
         create_menu_row("👤", "แก้ไขโปรไฟล์", "ชื่อ อีเมล"),
         create_menu_row("🔐", "เปลี่ยนรหัสผ่าน", "อัพเดทความปลอดภัย"),
         Divider(height=20), logout_btn],
        spacing=12,
        padding=16,
    )

# ==================== MAIN ====================
def main(page: Page):

        # ====== New Tab Structure (HTML ดีไซน์) ======
        def pomodoro_tab(page):
            return timer_screen(page)

        def task_tab(page):
            # --- ปุ่มสร้างงาน + popup ---

            def show_add_task_sheet():
                title_field = TextField(label="ชื่องาน", hint_text="เช่น พัฒนา API endpoint...", autofocus=True, bgcolor=PEACH_P, border_radius=12)
                note_field = TextField(label="หมายเหตุ (ไม่บังคับ)", multiline=True, min_lines=2, bgcolor=PEACH_P, border_radius=12)
                date_choice = [get_today_date()]
                status_msg = Text("", size=11, color=CORAL)
                submit_success = [False]

                # Date picker (เฉพาะวันนี้หรืออนาคต)
                def on_date_change(e):
                    if e.control.value:
                        picked = e.control.value
                        if picked < datetime.now().date():
                            status_msg.value = "❌ เลือกได้เฉพาะวันนี้หรืออนาคต"
                            page.update()
                            return
                        date_choice[0] = picked.strftime("%Y-%m-%d")
                        status_msg.value = ""
                        page.update()

                date_picker = ft.DatePicker(
                    on_change=on_date_change,
                    first_date=datetime.now().date(),
                    last_date=(datetime.now() + timedelta(days=365)).date(),
                )
                page.overlay.append(date_picker)

                def open_date_picker(e):
                    date_picker.pick_date()

                def on_submit(e):
                    if not title_field.value or not title_field.value.strip():
                        status_msg.value = "⚠️ กรุณากรอกชื่องาน"
                        page.update()
                        return
                    result = api_create_task(
                        user_id=USER_ID,
                        title=title_field.value.strip(),
                        note=note_field.value.strip() if note_field.value else "",
                        status="todo",
                        date_str=date_choice[0],
                    )
                    if result:
                        submit_success[0] = True
                        status_msg.value = "✅ สร้างงานสำเร็จ!"
                        # อัปเดตงานหน้าโฮมทันที
                        page.controls[0].content = home_screen(page)
                        page.update()
                        # ปิด popup อัตโนมัติหลัง 1.2 วิ
                        def close_sheet():
                            import time as _t; _t.sleep(1.2)
                            sheet.open = False
                            page.update()
                        import threading as _th; _th.Thread(target=close_sheet, daemon=True).start()
                    else:
                        status_msg.value = "❌ ไม่สามารถบันทึกได้ กรุณาตรวจสอบ API"
                        page.update()

                sheet_content = Column(
                    [
                        Text("เพิ่มงานใหม่", size=18, weight="bold", color=CORAL),
                        title_field,
                        note_field,
                        Text("วันที่", size=12, weight="bold"),
                        Row([
                            ElevatedButton(
                                date_choice[0],
                                bgcolor=AMBER,
                                color=DARK,
                                on_click=open_date_picker,
                                style=ButtonStyle(shape="rounded"),
                            ),
                        ], spacing=8),
                        status_msg,
                        ElevatedButton(
                            "✨ บันทึกงาน",
                            bgcolor=CORAL if not submit_success[0] else SAGE,
                            color="white",
                            width=300,
                            on_click=on_submit,
                            style=ButtonStyle(shape="rounded"),
                            disabled=submit_success[0],
                        ),
                    ],
                    spacing=12,
                )

                sheet.content = Container(sheet_content, padding=20, bgcolor="white", border_radius=24)
                sheet.open = True
                page.update()

            sheet = BottomSheet(Container(), on_dismiss=lambda e: page.update())
            page.overlay.append(sheet)

            # --- ปุ่ม + สี Peach/CORAL ---
            def add_btn():
                return Container(
                    IconButton(icons.ADD, icon_color="white", bgcolor=PEACH, width=48, height=48, on_click=lambda e: show_add_task_sheet()),
                    alignment=ft.alignment.Alignment(1, 1),
                    padding=8,
                )

            # --- แสดง home_screen + ปุ่ม + ---
            return Stack([
                home_screen(page),
                add_btn()
            ])

        def calendar_tab(page):
            # ต้องการ on_day_selected callback (dummy)
            def on_day_selected(day):
                pass
            return calendar_screen(page, on_day_selected)

        def music_tab(page):
            return music_player_screen(page)

        def profile_tab(page):
            return profile_screen(page)

        nav_tabs = [
            {"label": "โฟกัส", "icon": icons.TIMER, "builder": pomodoro_tab},
            {"label": "งาน", "icon": icons.CHECKLIST, "builder": task_tab},
            {"label": "ปฏิทิน", "icon": icons.CALENDAR_MONTH, "builder": calendar_tab},
            {"label": "เพลง", "icon": icons.MUSIC_NOTE, "builder": music_tab},
            {"label": "โปรไฟล์", "icon": icons.PERSON, "builder": profile_tab},
        ]
        selected_tab = [0]

        def on_nav_change(e):
            idx = e.control.selected_index
            selected_tab[0] = idx
            main_content.content = nav_tabs[idx]["builder"](page)
            page.update()

        main_content = Container(content=nav_tabs[0]["builder"](page), expand=True)

        nav_bar = NavigationBar(
            destinations=[
                NavigationBarDestination(icon=tab["icon"], label=tab["label"]) for tab in nav_tabs
            ],
            selected_index=0,
            on_change=on_nav_change,
            bgcolor=CARD,
            indicator_color=PEACH,
            label_behavior="alwaysShow",
        )

        page.add(
            Column([
                main_content,
                nav_bar
            ], expand=True, spacing=0)
        )

if __name__ == "__main__":
    import flet as ft
    ft.app(target=main)