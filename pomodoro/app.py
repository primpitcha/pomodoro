import flet as ft
# ✅ แก้ไข: ใน Flet 0.83.x Audio ถูกแยกออกเป็น package ต่างหาก
# ต้อง pip install flet-audio ก่อน แล้ว import แบบนี้
try:
    from flet_audio import Audio, ReleaseMode
    from flet_audio.types import AudioState
    AUDIO_AVAILABLE = True
except ImportError:
    AudioState = None  # type: ignore
    AUDIO_AVAILABLE = False
    print("⚠️  flet-audio ไม่ได้ติดตั้ง — รัน: pip install flet-audio")

from flet import (
    Icons as icons, ThemeMode, MainAxisAlignment, CrossAxisAlignment,
    ScrollMode, Text, Row, Column,
    Container, Stack, ProgressRing,
    ElevatedButton, TextButton, Card,
    ListView, Icon, Checkbox, Divider,
    NavigationBar, NavigationBarDestination, TextField,
    Page, LinearGradient, TextAlign, ButtonStyle, IconButton,
    AlertDialog
)
from datetime import datetime, timedelta, date
import asyncio
import threading
import time
import traceback
import requests
import os
import sys
from pathlib import Path
from assets.audio.audio_files import AUDIO_FILES

# ดึงความยาวไฟล์ mp3 แบบ “ของจริง”
try:
    from mutagen.mp3 import MP3  # type: ignore
    _MUTAGEN_AVAILABLE = True
except Exception:
    MP3 = None  # type: ignore
    _MUTAGEN_AVAILABLE = False

# ==================== Configuration ====================
_API_PORT_FILE = Path(__file__).resolve().parent / ".pomodoro_api_port"


def api_base() -> str:
    """URL ของ FastAPI — อ่านจากไฟล์ที่ pomodoro_api สร้างเมื่อเลือกพอร์ตจริง"""
    env = (os.environ.get("POMODORO_API_BASE") or "").strip()
    if env:
        return env.rstrip("/")
    try:
        if _API_PORT_FILE.is_file():
            p = int(_API_PORT_FILE.read_text(encoding="utf-8").strip())
            return "http://127.0.0.1:%d" % p
    except (ValueError, OSError):
        pass
    return "http://127.0.0.1:8000"

# ==================== Color Palette ====================
PEACH   = "#FF8C61"
CORAL   = "#E8624A"
AMBER   = "#F4A53C"
SAGE    = "#8CB87A"
DARK    = "#3D2C1E"
MID     = "#7A5C44"
SOFT    = "#B89880"
BG      = "#FFF8F0"
CARD    = "#FFFFFF"
PEACH_P = "#FFE8D6"
AMBER_P = "#FFF0C2"
LINE    = "#F0E6E0"
SHADOW  = "#F5D2C2"

# ==================== Global State ====================
current_user: dict = {}
_user_cache:  dict = {}

# ✅ เก็บ reference ของ Audio control ที่กำลังเล่นอยู่ (global)
_current_audio_control = None
_audio_disabled = False
_pygame_available = False
_pygame_inited = False
_pygame_current_path = None
_pygame_paused = False
_audio_paused = False
_selected_track_name = None  # เพลงที่เลือกล่าสุด (ค้างแม้ pause)

# --- เพลง: เล่นต่อคิว (จบแล้วไปเพลงถัดไป) + pygame / flet-audio ---
_music_current_idx = 0
_music_user_stopped_chain = False
_music_last_page = None
_music_chain_advancing = False
_music_play_session_id = 0
_pygame_music_watcher_started = False
_home_selected_date = None  # YYYY-MM-DD (วันที่ที่เลือกในหน้า Pomo Focus)
_home_show_all_tasks = False  # True=แสดง "ทั้งหมด (DB)" เป็นตัวเลือกเสริม
_home_active_task_id = None
_home_focus_state = {
    "task_id": None,
    "mode": "work",
    "is_running": False,
    "is_paused": False,
    "cur_time": 0,
    "completed_rounds": 0,
    "planned_rounds": 1,
    "started_at": None,
}
_home_timer_ring_ref = None
_home_timer_text_ref = None
try:
    import pygame  # type: ignore

    _pygame_available = True
except Exception:
    _pygame_available = False

my_tracks = [
    {"id": 1, "name": "แล้วเราจะได้รักกันไหม - ณเดชน์ คุกิมิยะ ft.ญาญ่า",   "category": "เพลงละครฟังสบาย",  "icon_color": PEACH , "file": "audio/Doyouloveme.mp3"},
    {"id": 2, "name": "หนึ่งเดียวคือเธอ - เจมส์ จิรายุ","category": "เพลงละครฟังสบาย",  "icon_color": SAGE , "file": "audio/OnlyYou.mp3"},
    {"id": 3, "name": "รักแท้อยู่เหนือกาลเวลา - โดม จารุวัฒน์",   "category": "เพลงละครฟังสบาย", "icon_color": "#4DA6FF", "file": "audio/love_song.mp3"},
    {"id": 4, "name": "Falling Behind - laufey",   "category": "เพลงแจ๊สเพราะๆ", "icon_color": AMBER , "file": "audio/fallingbehind.mp3"},
    {"id": 5, "name": "From the start - laufey", "category": "เพลงแจ๊สเพราะๆ", "icon_color": "#9966FF" , "file": "audio/fromthestart.mp3"},
    {"id": 6, "name": "Blue bossa - Advanced Jazz","category": "เพลงแจ๊สเพราะๆ", "icon_color": CORAL , "file": "audio/BlueBossa.mp3"},
    {"id": 7, "name": "At My Worst - Pink Sweat", "category": "เพลงชิลฟีลคาเฟ่", "icon_color": CORAL , "file": "audio/AtMyWorst.mp3"},
    {"id": 8, "name": "Call You Mine - Jeff Bernat", "category": "เพลงชิลฟีลคาเฟ่", "icon_color": CORAL , "file": "audio/CallYouMine.mp3"},
]

# ค่าเริ่มต้นของเพลงที่ต้องมีไฟล์จริงใน `AUDIO_FILES`
DEFAULT_MUSIC_TRACK = my_tracks[0]["name"] if my_tracks else next(iter(AUDIO_FILES.keys()), "ไม่ได้เลือกเพลง")

# ==================== Music Duration + Elapsed ====================
# เก็บความยาวรวม (วินาที) ของแต่ละเพลง เพื่อแสดง duration ที่ “ถูกต้องจากไฟล์จริง”
_track_total_duration_sec = {}

# สำหรับคำนวณเวลา elapsed ระหว่างเพลงกำลังเล่น
_music_started_at_monotonic = None
_music_elapsed_before_pause_sec = 0.0

# token สำหรับหยุด/เริ่ม loop อัปเดตเวลาในหน้า music_screen
_music_elapsed_tick_token = 0

# ตัวกรองหมวดหมู่เพลง (ใช้ใน music_screen)
_music_category_filter = "ทั้งหมด"

def _sec_to_mmss(sec) -> str:
    sec_int = max(0, int(sec))
    m = sec_int // 60
    s = sec_int % 60
    return f"{m}:{s:02d}"

def _load_music_durations_from_files():
    global _track_total_duration_sec, MP3, _MUTAGEN_AVAILABLE
    base_dir = Path(__file__).parent / "assets"

    # เผื่อว่าติดตั้ง mutagen หลังจากเริ่มรันแอป (ให้ลอง import ใหม่อีกครั้ง)
    if not _MUTAGEN_AVAILABLE:
        try:
            from mutagen.mp3 import MP3 as _MP3  # type: ignore
            MP3 = _MP3  # type: ignore
            _MUTAGEN_AVAILABLE = True
        except Exception:
            pass

    # ป้องกันคำนวณซ้ำ แต่ถ้ารอบก่อนยังไม่ได้ duration เลย ให้ลองใหม่ได้
    if getattr(_load_music_durations_from_files, "_loaded", False) and _track_total_duration_sec:
        return
    _load_music_durations_from_files._loaded = True  # type: ignore[attr-defined]

    printed_fail = set()
    for t in my_tracks:
        track_name = t["name"]
        rel = AUDIO_FILES.get(track_name)
        total_sec = None

        if _MUTAGEN_AVAILABLE and rel:
            abs_path = str((base_dir / rel).resolve())
            if os.path.exists(abs_path):
                try:
                    audio = MP3(abs_path)  # type: ignore[misc]
                    total_sec = float(audio.info.length)
                except Exception:
                    total_sec = None
                    if track_name not in printed_fail:
                        printed_fail.add(track_name)
                        print(f"[MUSIC_DURATION] mutagen อ่านไฟล์ไม่ได้: {track_name}")

        # fallback: บางไฟล์อ่าน metadata ไม่ผ่าน แต่ยังเล่นได้ด้วย pygame
        if total_sec is None and _pygame_available and rel:
            abs_path = str((base_dir / rel).resolve())
            if os.path.exists(abs_path):
                try:
                    if not _pygame_inited:
                        pygame.mixer.init()
                    snd = pygame.mixer.Sound(abs_path)
                    total_sec = float(snd.get_length())
                except Exception:
                    total_sec = None

        if total_sec is None:
            continue

        total_sec_int = max(0, int(round(float(total_sec))))
        _track_total_duration_sec[track_name] = total_sec_int
        t["duration_sec"] = total_sec_int

_load_music_durations_from_files()

def _get_music_elapsed_sec() -> float:
    # ถ้ากด pause ไว้ elapsed จะหยุดค้างที่ค่า “ก่อน pause”
    global _music_started_at_monotonic, _music_elapsed_before_pause_sec
    if _music_started_at_monotonic is None:
        return float(_music_elapsed_before_pause_sec)
    if _audio_paused or _pygame_paused:
        return float(_music_elapsed_before_pause_sec)
    return float(_music_elapsed_before_pause_sec) + (time.monotonic() - _music_started_at_monotonic)

# ==================== API Helpers ====================
def _get(path, timeout=5):
    try:
        r = requests.get(f"{api_base()}{path}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[GET {path}] {e}")
    return None

def _post(path, payload, timeout=5):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[POST {path}] {e}")
    return None

def _put(path, payload, timeout=5):
    try:
        r = requests.put(f"{api_base()}{path}", json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[PUT {path}] {e}")
    return None

def _delete(path, timeout=5):
    try:
        r = requests.delete(f"{api_base()}{path}", timeout=timeout)
        return r.status_code == 200
    except Exception as e:
        print(f"[DELETE {path}] {e}")
    return False

def api_login(username, email, password):
    return _post("/login", {"username": username, "email": email, "password": password})

def api_register(username, email, password):
    return _post("/register", {"username": username, "email": email, "password": password})

def api_get_user(user_id):
    return _get(f"/users/{user_id}")

def api_get_tasks_by_date(user_id, date_str):
    return _get(f"/tasks/{user_id}/{date_str}") or []

def api_get_all_tasks(user_id):
    return _get(f"/tasks/all/{user_id}") or []

def api_create_task(user_id, title, note, status, date_str):
    return _post("/tasks", {"user_id": user_id, "title": title,
                             "note": note or "", "status": status, "date": date_str})

def api_update_task(task_id, **kwargs):
    return _put(f"/tasks/{task_id}", {k: v for k, v in kwargs.items() if v is not None})

def api_delete_task(task_id):
    return _delete(f"/tasks/{task_id}")

def api_create_session(user_id, task_id, session_type, duration_minutes,
                        started_at, ended_at=None, completed=True):
    return _post("/sessions", {
        "user_id": user_id, "task_id": task_id,
        "session_type": session_type, "duration_minutes": duration_minutes,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat() if ended_at else None,
        "completed": completed,
    })

def api_get_stats(user_id):
    return _get(f"/sessions/{user_id}/stats") or {
        "today_sessions": 0, "today_tasks_done": 0, "today_focus_hours": 0,
        "total_sessions": 0, "total_tasks_done": 0, "total_focus_hours": 0,
    }

def api_update_settings(user_id, settings: dict) -> bool:
    result = _put(f"/users/{user_id}/settings", settings)
    return result is not None

def api_update_profile(user_id, username=None, email=None):
    payload = {}
    if username is not None:
        payload["username"] = username
    if email is not None and email != "":
        payload["email"] = email
    return _put(f"/users/{user_id}/profile", payload)

def api_change_password(user_id, old_password, new_password):
    return _put(f"/users/{user_id}/password",
                {"old_password": old_password, "new_password": new_password})

# ==================== Cache ====================
def get_user_data():
    global _user_cache, current_user
    uid = current_user.get("id", 1)
    if not _user_cache or _user_cache.get("id") != uid:
        data = api_get_user(uid)
        if data:
            s = data.get("settings") or {}
            selected_music_track = s.get("selected_music_track")
            # กันค่าที่เก็บไว้เป็นชื่อเพลงที่ไม่มีไฟล์จริง (เช่นเคยเป็น mock/ชื่อเดิม)
            if not selected_music_track or selected_music_track not in AUDIO_FILES:
                selected_music_track = DEFAULT_MUSIC_TRACK
            _user_cache = {
                "id": data["id"],
                "username": data["username"],
                "email": data["email"],
                "created_at": data["created_at"],
                "work_minutes":             s.get("work_minutes", 25),
                "short_break_minutes":      s.get("short_break_minutes", 5),
                "long_break_minutes":       s.get("long_break_minutes", 15),
                "rounds_before_long_break": s.get("rounds_before_long_break", 4),
                "selected_music_track":     selected_music_track,
            }
        else:
            _user_cache = {
                "id": uid,
                "username": current_user.get("username", "ผู้ใช้"),
                "email": current_user.get("email", ""),
                "created_at": datetime.now().isoformat(),
                "work_minutes": 25, "short_break_minutes": 5,
                "long_break_minutes": 15, "rounds_before_long_break": 4,
                "selected_music_track": DEFAULT_MUSIC_TRACK,
            }
    return _user_cache

# region agent log
_AGENT_DEBUG_LOG = Path(__file__).resolve().parent / "debug-1f9c80.log"

def _agent_debug_log(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "pre-fix"):
    try:
        import json
        payload = {
            "sessionId": "1f9c80",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_AGENT_DEBUG_LOG, "a", encoding="utf-8") as _f:
            _f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

# endregion

# ==================== Utilities ====================
def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_week_dates():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(6)]

def get_thai_day_name(date_obj):
    return ["จ","อ","พ","พฤ","ศ","ส","อา"][date_obj.weekday()]

def get_thai_month_name(month=None):
    m = ["","ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
    return m[month or datetime.now().month]

def get_status_color(status):
    return {"todo": PEACH, "in_progress": AMBER, "done": SAGE}.get(status, PEACH)

def get_status_text(status):
    return {"todo": "ยังไม่เริ่ม", "in_progress": "กำลังทำ", "done": "เสร็จแล้ว"}.get(status, status)

def pack_task_note(note: str, est_pomodoros: int, act_pomodoros: int = 0) -> str:
    """เก็บ est/act ใน note: [POMO:est|act] ข้อความอธิบาย"""
    clean = (note or "").strip()
    est = max(1, est_pomodoros)
    act = max(0, min(int(act_pomodoros), est))
    return f"[POMO:{est}|{act}] {clean}".strip()

def unpack_task_note(note: str):
    """คืน (est, clean_note, act) — รองรับ [POMO:4] เดิม และ [POMO:4|2]"""
    raw = (note or "").strip()
    est, act = 1, 0
    clean = raw
    if raw.startswith("[POMO:"):
        end = raw.find("]")
        if end != -1:
            inner = raw[6:end]
            if "|" in inner:
                a, b = inner.split("|", 1)
                if a.isdigit():
                    est = max(1, int(a))
                if b.strip().isdigit():
                    act = max(0, int(b.strip()))
            elif inner.isdigit():
                est = max(1, int(inner))
            clean = raw[end + 1 :].strip()
    act = min(act, est)
    return est, clean, act


def total_chain_minutes_for_pomodoros(
    num_work_sessions: int,
    work_min: int,
    short_min: int,
    long_min: int,
    rounds_before_long: int,
) -> int:
    """เวลารวม (นาที) สำหรับ R รอบโฟกัสต่อเนื่อง มีพักระหว่างรอบตามกฎ pomodoro"""
    R = max(0, int(num_work_sessions))
    if R <= 0:
        return 0
    k = max(1, int(rounds_before_long))
    mins = R * work_min
    for i in range(1, R):
        mins += long_min if (i % k == 0) else short_min
    return mins

# ==================== Audio Playback Helper (FIXED) ====================
def _audio_packaging_hint() -> str:
    # sys.frozen is set by PyInstaller-style packagers
    if getattr(sys, "frozen", False):
        return (
            "ดูเหมือนคุณกำลังรันแบบ build/pack อยู่\n"
            "ให้ rebuild โดยใส่แพ็กเกจเสริมนี้เข้าไปด้วย เช่น:\n"
            "- flet build windows --include-packages flet_audio\n"
            "- flet build apk --include-packages flet_audio\n"
            "- flet build ipa --include-packages flet_audio\n"
        )
    return (
        "ถ้าคุณกำลัง build/pack แอป ให้ใส่ `--include-packages flet_audio` ตอน build\n"
        "ถ้ารันปกติให้ลอง `pip install -U flet flet-audio` แล้วรันใหม่"
    )


def _show_audio_error(page: Page, title: str, detail: str):
    def _close(e):
        dlg.open = False
        page.update()

    def _disable(e):
        global _audio_disabled
        _audio_disabled = True
        stop_music_playback(page)
        dlg.open = False
        page.update()

    dlg = AlertDialog(
        title=Row([Icon(icons.ERROR_OUTLINE, color=CORAL), Text(title, color=CORAL, weight="bold")], spacing=8),
        content=Text(detail, size=12, color=DARK),
        actions=[
            TextButton("ปิดเสียงชั่วคราว", on_click=_disable),
            ft.ElevatedButton("ปิด", bgcolor=CORAL, color="white", on_click=_close),
        ],
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def stop_current_audio(page: Page):
    """
    หยุดและลบ Audio control เดิมออกจาก overlay
    ใช้ได้ทั้ง flet-audio และ fallback
    """
    global _current_audio_control, _audio_paused
    global _music_started_at_monotonic, _music_elapsed_before_pause_sec
    if _current_audio_control is not None:
        try:
            # flet-audio methods are async; best-effort call and ignore if unsupported
            _current_audio_control.pause()
        except Exception:
            pass
        try:
            if _current_audio_control in page.overlay:
                page.overlay.remove(_current_audio_control)
        except Exception:
            pass
        _current_audio_control = None
    _audio_paused = False
    _music_started_at_monotonic = None
    _music_elapsed_before_pause_sec = 0.0

    # ✅ ล้าง Audio control เก่าทุกตัวที่ยังค้างอยู่ใน overlay
    to_remove = [c for c in page.overlay if isinstance(c, Audio)] if AUDIO_AVAILABLE else []
    for c in to_remove:
        try:
            c.pause()
        except Exception:
            pass
        page.overlay.remove(c)

    # pygame fallback — เคลียร์ path ก่อน แล้วค่อย stop เพื่อไม่ให้ watcher คิดว่าเพลงจบเอง
    global _pygame_inited, _pygame_current_path, _pygame_paused
    _pygame_current_path = None
    _pygame_paused = False
    if _pygame_available and _pygame_inited:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


def stop_music_playback(page: Page):
    """หยุดเล่นและไม่ให้โซ่เพลงเล่นต่อเอง จนกว่าจะกดเล่นเพลงใหม่"""
    global _music_user_stopped_chain
    _music_user_stopped_chain = True
    stop_current_audio(page)


def _music_playlist_names() -> list:
    return [t["name"] for t in my_tracks]


def _music_sync_index(track_name: str):
    global _music_current_idx
    names = _music_playlist_names()
    try:
        _music_current_idx = names.index(track_name)
    except ValueError:
        _music_current_idx = 0


def _persist_selected_music_track_to_db(track_name: str):
    """เก็บแค่ “เพลงล่าสุดที่เลือก” ลง DB (ไม่ใช่ประวัติการฟังทั้งหมด)"""
    try:
        uid = current_user.get("id")
        if not uid or not track_name:
            return
        # ส่งไป background thread เพื่อไม่ให้ UI กระตุก
        threading.Thread(
            target=api_update_settings,
            args=(uid, {"selected_music_track": track_name}),
            daemon=True,
        ).start()
    except Exception:
        # ความล้มเหลวในการบันทึกค่าไม่ควรไปกระทบการเล่นเพลง
        pass


def _ensure_pygame_music_watcher():
    """ลูปพื้นหลัง: เมื่อ pygame music จบโดยธรรมชาติ ให้ไปเพลงถัดไป"""
    global _pygame_music_watcher_started
    if _pygame_music_watcher_started:
        return
    _pygame_music_watcher_started = True

    def _loop():
        last_busy = False
        while True:
            time.sleep(0.22)
            try:
                if not _pygame_available or not _pygame_inited:
                    last_busy = False
                    continue
                if _pygame_current_path is None:
                    last_busy = False
                    continue
                busy = pygame.mixer.music.get_busy()
                if last_busy and (not busy) and (not _pygame_paused):
                    _schedule_music_track_advance()
                    last_busy = False
                else:
                    last_busy = busy
            except Exception:
                pass

    threading.Thread(target=_loop, daemon=True).start()


def _schedule_music_track_advance():
    global _music_chain_advancing, _music_last_page
    page = _music_last_page
    if page is None or _music_user_stopped_chain or _audio_disabled:
        return
    if _music_chain_advancing:
        return
    _music_chain_advancing = True

    async def _go():
        global _music_chain_advancing
        try:
            await asyncio.sleep(0.06)
            if not _music_user_stopped_chain:
                _advance_music_playlist(page)
        finally:
            _music_chain_advancing = False

    try:
        page.run_task(_go())
    except Exception:
        _music_chain_advancing = False


def _advance_music_playlist(page: Page):
    names = _music_playlist_names()
    if not names or _music_user_stopped_chain:
        return
    next_i = (_music_current_idx + 1) % len(names)
    _play_music_track(page, names[next_i], user_started=False)


def _play_music_track(
    page: Page,
    track_name: str,
    *,
    user_started: bool = False,
):
    """
    เล่นเพลงหนึ่งเพลง (ไม่วนซ้ำในไฟล์เดียว) — จบแล้วไปเพลงถัดไปในรายการ my_tracks วนรอบ
    """
    global _current_audio_control, _selected_track_name, _music_last_page
    global _music_play_session_id, _pygame_inited, _pygame_current_path
    global _music_user_stopped_chain
    global _music_started_at_monotonic, _music_elapsed_before_pause_sec

    if _audio_disabled:
        return
    _music_last_page = page
    if user_started:
        _music_user_stopped_chain = False

    audio_path = AUDIO_FILES.get(track_name)
    if not audio_path:
        print(f"⚠️  ไม่พบไฟล์เพลงสำหรับ: {track_name}")
        return

    _music_play_session_id += 1
    play_sid = _music_play_session_id

    _selected_track_name = track_name
    if user_started:
        # บันทึกเฉพาะ “เพลงล่าสุดที่ผู้ใช้เลือก” ลง DB (ไม่ใช่ประวัติการฟังทั้งหมด)
        if _user_cache is not None:
            _user_cache["selected_music_track"] = track_name
        _persist_selected_music_track_to_db(track_name)
    _music_sync_index(track_name)

    stop_current_audio(page)

    if _pygame_available and sys.platform.startswith("win"):
        try:
            if not _pygame_inited:
                pygame.mixer.init()
                _pygame_inited = True
            abs_path = str((Path(__file__).parent / "assets" / audio_path).resolve())
            pygame.mixer.music.load(abs_path)
            pygame.mixer.music.play(loops=0)
            _pygame_current_path = abs_path
            # เริ่มนับเวลาเมื่อเล่นสำเร็จจริง
            _music_elapsed_before_pause_sec = 0.0
            _music_started_at_monotonic = time.monotonic()
            _ensure_pygame_music_watcher()
            print(f"▶ เล่นเพลง (pygame): {track_name} ({abs_path})")
            try:
                page.update()
            except Exception:
                pass
            return
        except Exception as ex:
            _show_audio_error(
                page,
                "เล่นเพลงไม่ได้ (pygame)",
                f"{ex}\n\nตรวจสอบว่าไฟล์อยู่ที่ `assets/{audio_path}` และเป็นไฟล์ .mp3 ที่เล่นได้",
            )
            return

    if not AUDIO_AVAILABLE:
        _show_audio_error(
            page,
            "เล่นเพลงไม่ได้ (ยังไม่ได้ติดตั้งส่วนเสริมเสียง)",
            "ให้ติดตั้งด้วยคำสั่ง: pip install flet-audio\n\n" + _audio_packaging_hint(),
        )
        return

    def _on_state_change(e):
        if not AUDIO_AVAILABLE or AudioState is None:
            return
        try:
            if e.state == AudioState.COMPLETED and play_sid == _music_play_session_id:
                _schedule_music_track_advance()
        except Exception:
            pass

    audio_ctrl = Audio(
        src=audio_path,
        autoplay=True,
        volume=1.0,
        release_mode=ReleaseMode.RELEASE,
        on_state_change=_on_state_change,
    )
    _current_audio_control = audio_ctrl
    page.overlay.append(audio_ctrl)
    # เริ่มนับเวลาเมื่อสร้าง audio control สำเร็จ
    _music_elapsed_before_pause_sec = 0.0
    _music_started_at_monotonic = time.monotonic()
    try:
        page.update()
    except Exception as ex:
        stop_current_audio(page)
        _show_audio_error(
            page,
            "เล่นเพลงไม่ได้ (Audio control ไม่พร้อม)",
            f"{ex}\n\n{_audio_packaging_hint()}",
        )
        return
    print(f"▶ เล่นเพลง: {track_name}  ({audio_path})")


def pause_current_audio(page: Page):
    """พักชั่วคราว (ไม่รีเซ็ตตำแหน่ง) รองรับ pygame + flet-audio"""
    global _audio_paused, _pygame_paused
    global _music_started_at_monotonic, _music_elapsed_before_pause_sec

    # freeze elapsed time
    if _music_started_at_monotonic is not None and not (_audio_paused or _pygame_paused):
        _music_elapsed_before_pause_sec += (time.monotonic() - _music_started_at_monotonic)
        _music_started_at_monotonic = None

    if _pygame_available and _pygame_inited and _pygame_current_path is not None:
        try:
            pygame.mixer.music.pause()
            _pygame_paused = True
        except Exception:
            pass

    if _current_audio_control is not None:
        async def _pause():
            try:
                await _current_audio_control.pause()
            except Exception:
                # fallback for non-async pause()
                try:
                    _current_audio_control.pause()
                except Exception:
                    pass

        try:
            page.run_task(_pause)
            _audio_paused = True
        except Exception:
            pass


def resume_current_audio(page: Page):
    """เล่นต่อจากเดิม (resume)"""
    global _audio_paused, _pygame_paused
    global _music_started_at_monotonic

    # resume elapsed time counter
    if _music_started_at_monotonic is None and (_audio_paused or _pygame_paused):
        _music_started_at_monotonic = time.monotonic()

    if _pygame_available and _pygame_inited and _pygame_current_path is not None and _pygame_paused:
        try:
            pygame.mixer.music.unpause()
            _pygame_paused = False
        except Exception:
            pass

    if _current_audio_control is not None and _audio_paused:
        async def _resume():
            try:
                await _current_audio_control.resume()
            except Exception:
                # fallback: try play() which might resume depending on implementation
                try:
                    await _current_audio_control.play()
                except Exception:
                    try:
                        _current_audio_control.resume()
                    except Exception:
                        pass

        try:
            page.run_task(_resume)
            _audio_paused = False
        except Exception:
            pass


def play_audio(page: Page, track_name: str):
    """
    Helper สำหรับเล่นเพลงจาก track_name
    ใช้ใน home_screen / ส่วนอื่นที่ไม่ใช่ music_screen
    """
    _play_music_track(page, track_name, user_started=True)


# ==================== ADD TASK DIALOG ====================
def show_add_task_dialog(page: Page, on_done):
    today_str = get_today_date()

    title_field = TextField(
        label="ชื่องาน *", hint_text="เช่น ทำรายงาน, พัฒนา API...",
        autofocus=True, bgcolor=PEACH_P, border_radius=12,
        text_style=ft.TextStyle(color=DARK),
    )
    note_field = TextField(
        label="หมายเหตุ (ไม่บังคับ)", multiline=True, min_lines=2,
        bgcolor=PEACH_P, border_radius=12,
        text_style=ft.TextStyle(color=DARK),
    )
    est_pomo_field = TextField(
        label="จำนวนรอบ (Pomodoros)",
        value="1",
        width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=PEACH_P,
        border_radius=12,
        text_style=ft.TextStyle(color=DARK),
    )
    status_msg   = Text("", size=12, color=CORAL)

    dlg = AlertDialog(open=False)

    def on_submit(e):
        if not title_field.value or not title_field.value.strip():
            status_msg.value = "กรุณากรอกชื่องาน"
            page.update()
            return
        est_raw = (est_pomo_field.value or "1").strip()
        if not est_raw.isdigit() or int(est_raw) <= 0:
            status_msg.value = "จำนวนรอบต้องเป็นตัวเลขมากกว่า 0"
            page.update()
            return
        est_pomos = int(est_raw)

        uid = current_user.get("id", 1)
        result = api_create_task(
            user_id=uid,
            title=title_field.value.strip(),
            note=pack_task_note(note_field.value.strip() if note_field.value else "", est_pomos),
            status="todo",
            date_str=today_str,
        )
        if result:
            global _home_selected_date
            _home_selected_date = today_str
            status_msg.value = "บันทึกสำเร็จ"
            status_msg.color = SAGE
            page.update()
            on_done()
            import time; time.sleep(0.5)
            dlg.open = False
            page.update()

    def on_cancel(e):
        dlg.open = False
        page.update()

    dlg.title = Row([
        Icon(icons.ADD_TASK, color=CORAL, size=22),
        Text("เพิ่มงานใหม่", size=18, weight="bold", color=CORAL),
    ], spacing=8)

    dlg.content = Container(
        Column([
            title_field,
            note_field,
            est_pomo_field,
            Container(height=4),
            Row([
                Icon(icons.CALENDAR_TODAY, color=DARK, size=16),
                Text(f"บันทึกเป็นงานวันนี้ ({today_str})", size=12, color=SOFT),
            ], spacing=6, vertical_alignment=CrossAxisAlignment.CENTER),
            status_msg,
        ], spacing=12, tight=True),
        width=360, padding=ft.padding.only(top=8),
    )

    dlg.actions = [
        TextButton("ยกเลิก", on_click=on_cancel),
        ft.ElevatedButton(
            "บันทึกงาน",
            icon=icons.SAVE,
            bgcolor=CORAL,
            color="white",
            on_click=on_submit,
        ),
    ]

    page.overlay.append(dlg)
    dlg.open = True
    page.update()

# ==================== LOGIN SCREEN ====================
def build_login_screen(page: Page, on_login_success):
    username_field = TextField(
        label="Username", hint_text="ชื่อผู้ใช้",
        border_radius=14, bgcolor=PEACH_P, border_color=PEACH,
        prefix_icon=icons.PERSON,
        text_style=ft.TextStyle(color=DARK),
    )
    email_field = TextField(
        label="Email", hint_text="อีเมลของคุณ",
        border_radius=14, bgcolor=PEACH_P, border_color=PEACH,
        prefix_icon=icons.EMAIL,
        text_style=ft.TextStyle(color=DARK),
    )
    pass_field = TextField(
        label="Password", password=True, can_reveal_password=True,
        border_radius=14, bgcolor=PEACH_P, border_color=PEACH,
        prefix_icon=icons.LOCK,
        text_style=ft.TextStyle(color=DARK),
    )
    msg_text = Text("", size=12, color=CORAL, text_align=TextAlign.CENTER)
    loading  = ProgressRing(width=24, height=24, color=CORAL, visible=False)

    def set_loading(val: bool):
        loading.visible = val; page.update()

    def do_login(e):
        if not username_field.value or not email_field.value or not pass_field.value:
            msg_text.value = "กรุณากรอกข้อมูลให้ครบ"
            page.update()
            return
        set_loading(True)
        try:
            res = api_login(username_field.value.strip(),
                            email_field.value.strip(),
                            pass_field.value.strip())
            if res and res.get("status") == "success":
                on_login_success(res["user"])
            else:
                msg_text.value = "อีเมลหรือรหัสผ่านไม่ถูกต้อง"
        except Exception as ex:
            msg_text.value = f"เชื่อมต่อเซิร์ฟเวอร์ไม่ได้: {ex}"
        set_loading(False)

    def do_register(e):
        if not username_field.value or not email_field.value or not pass_field.value:
            msg_text.value = "กรุณากรอกข้อมูลให้ครบ"
            page.update()
            return
        set_loading(True)
        try:
            res = api_register(username_field.value.strip(),
                               email_field.value.strip(),
                               pass_field.value.strip())
            if res and res.get("status") == "success":
                msg_text.value = "สมัครสำเร็จ กด Log In เพื่อเข้าสู่ระบบ"
                msg_text.color = SAGE
            else:
                msg_text.value = "สมัครไม่สำเร็จ (อาจมีอีเมลนี้แล้ว)"
        except Exception as ex:
            msg_text.value = f"เชื่อมต่อเซิร์ฟเวอร์ไม่ได้: {ex}"
        set_loading(False)

    logo = Column([
        Icon(icons.TIMER, size=64, color=CORAL),
        Text("Pomo Focus", size=32, weight="bold", color=CORAL,
             text_align=TextAlign.CENTER),
        Text("จดจ่อ • ทำงาน • พักผ่อน", size=14, color=SOFT,
             text_align=TextAlign.CENTER),
    ], alignment=MainAxisAlignment.CENTER,
       horizontal_alignment=CrossAxisAlignment.CENTER, spacing=6)

    form_card = Container(
        Column([
            logo,
            Container(height=8),
            username_field, email_field, pass_field,
            loading, msg_text,
            ft.ElevatedButton(
                "Log In",
                icon=icons.LOGIN,
                bgcolor=CORAL,
                color="white",
                width=340,
                height=50,
                on_click=do_login,
                style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
            ),
            TextButton("ยังไม่มีบัญชี? สมัครสมาชิก", on_click=do_register,
                       style=ButtonStyle(color=SOFT)),
        ], alignment=MainAxisAlignment.CENTER,
           horizontal_alignment=CrossAxisAlignment.CENTER, spacing=14),
        padding=36, bgcolor=CARD, border_radius=28,
        shadow=ft.BoxShadow(blur_radius=32, color="#FFD6C2", offset=ft.Offset(0, 8)),
        width=400,
    )

    return Container(
        Column([form_card], alignment=MainAxisAlignment.CENTER,
               horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
        expand=True, bgcolor=BG,
        alignment=ft.Alignment(0, 0),
        padding=32,
    )

# ==================== HOME SCREEN ====================
def home_screen(page: Page):
    user_data   = get_user_data()
    today       = get_today_date()
    global _home_selected_date
    if not _home_selected_date:
        _home_selected_date = today
    selected_date = today
    global _home_show_all_tasks
    uid = current_user.get("id", user_data.get("id", 1))

    # ดึง tasks ทั้งหมดครั้งเดียว แล้วกรองตามวันที่เลือก
    all_tasks = api_get_all_tasks(uid) or []
    selected_tasks = [t for t in all_tasks if (t.get("date") or "")[:10] == selected_date]
    # แบบ A: งานค้างจากวันก่อน (ไม่ย้ายวันที่ใน DB)
    overdue_tasks = [
        t for t in all_tasks
        if (t.get("date") or "")[:10] < today and (t.get("status") or "") != "done"
    ]
    stats       = api_get_stats(uid)
    print(f"[HOME] uid={uid} selected_date={selected_date} tasks={len(selected_tasks)}")

    today_tasks = [t for t in all_tasks if (t.get("date") or "")[:10] == today]

    def scard(label, value, color, title_icon=None):
        if title_icon is not None:
            title = Row(
                [
                    Icon(title_icon, size=13, color=color),
                    Text(label, size=11, color=DARK),
                ],
                spacing=4,
                tight=True,
                alignment=MainAxisAlignment.CENTER,
            )
        else:
            title = Text(label, size=11, color=DARK)
        return Card(
            Container(
                Column(
                    [
                        title,
                        Text(str(value), size=24, weight="bold", color=color),
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=16,
            ),
            expand=True,
        )

    stats_row = Row(
        [
            scard("รอบวันนี้", stats["today_sessions"], PEACH, icons.TIMER),
            scard("งานเสร็จ", stats["today_tasks_done"], SAGE, icons.CHECK_CIRCLE),
            scard("โฟกัสวันนี้", f"{stats['today_focus_hours']}h", AMBER, icons.SCHEDULE),
        ],
        spacing=8,
    )

    global _home_active_task_id, _home_focus_state
    today_todo = [t for t in today_tasks if (t.get("status") or "") != "done"]
    today_ids = [t.get("id") for t in today_todo]
    if _home_active_task_id not in today_ids:
        _home_active_task_id = today_ids[0] if today_ids else None

    active_task = next((t for t in today_todo if t.get("id") == _home_active_task_id), None)
    planned_rounds = unpack_task_note(active_task.get("note") or "")[0] if active_task else 1

    work_s = user_data["work_minutes"] * 60
    short_s = user_data["short_break_minutes"] * 60
    long_s = user_data["long_break_minutes"] * 60

    def mode_seconds(mode: str) -> int:
        if mode == "short_break":
            return short_s
        if mode == "long_break":
            return long_s
        return work_s

    if _home_focus_state["task_id"] != _home_active_task_id:
        _est0, _, _act0 = unpack_task_note(active_task.get("note") or "") if active_task else (1, "", 0)
        _home_focus_state = {
            "task_id": _home_active_task_id,
            "mode": "work",
            "is_running": False,
            "is_paused": False,
            "cur_time": work_s,
            "completed_rounds": _act0,
            "planned_rounds": planned_rounds,
            "started_at": None,
        }
    else:
        _home_focus_state["planned_rounds"] = planned_rounds
        if active_task and not _home_focus_state.get("is_running"):
            _, _, act_db = unpack_task_note(active_task.get("note") or "")
            _home_focus_state["completed_rounds"] = act_db
        if _home_focus_state["cur_time"] <= 0:
            _home_focus_state["cur_time"] = mode_seconds(_home_focus_state.get("mode", "work"))

    def _fmt(sec: int):
        return f"{max(0, sec)//60:02d}:{max(0, sec)%60:02d}"

    current_total = mode_seconds(_home_focus_state["mode"])

    # controls สำหรับอัปเดตเวลาและ progress แบบ real-time
    timer_ring = ProgressRing(
        value=_home_focus_state["cur_time"] / max(1, current_total),
        width=200,
        height=200,
        stroke_width=14,
        color=CORAL,
        bgcolor="#F8DCCB",
    )
    timer_text = Text(_fmt(_home_focus_state["cur_time"]), size=40, weight="bold", color=CORAL)
    global _home_timer_ring_ref, _home_timer_text_ref
    _home_timer_ring_ref = timer_ring
    _home_timer_text_ref = timer_text

    async def _focus_tick():
        global _home_active_task_id, _home_timer_ring_ref, _home_timer_text_ref
        while _home_focus_state["is_running"] and _home_focus_state["cur_time"] > 0:
            await asyncio.sleep(1)
            if not _home_focus_state["is_running"]:
                break
            _home_focus_state["cur_time"] -= 1
            # อัปเดตเฉพาะหน้าปัดมะเขือเทศและเวลา โดยไม่รีเซ็ต scroll
            try:
                rem = max(0, _home_focus_state["cur_time"])
                latest_total = mode_seconds(_home_focus_state.get("mode", "work"))
                if _home_timer_ring_ref is not None:
                    _home_timer_ring_ref.value = rem / max(1, latest_total)
                if _home_timer_text_ref is not None:
                    _home_timer_text_ref.value = _fmt(rem)
            except Exception:
                pass
            try:
                page.update()
            except Exception:
                pass

        if _home_focus_state["is_running"] and _home_focus_state["cur_time"] == 0:
            _home_focus_state["cur_time"] = 0
            try:
                if _home_timer_ring_ref is not None:
                    _home_timer_ring_ref.value = 0.0
                if _home_timer_text_ref is not None:
                    _home_timer_text_ref.value = _fmt(0)
                page.update()
            except Exception:
                pass
            _home_focus_state["is_running"] = False
            _home_focus_state["is_paused"] = False
            if _home_focus_state["mode"] == "work":
                _home_focus_state["completed_rounds"] += 1

                _cr = _home_focus_state["completed_rounds"]
                round_minutes = max(1, int(user_data["work_minutes"]))
                ended_at = datetime.now()
                started_at = _home_focus_state["started_at"] or (ended_at - timedelta(minutes=round_minutes))
                task_id_for_session = active_task.get("id") if active_task else None

                def _persist_work_round():
                    # บันทึกทุก "รอบ work" เพื่อให้สถิติขึ้นตามเวลาจริง
                    api_create_session(
                        uid, task_id_for_session, "work", round_minutes,
                        started_at, ended_at, True,
                    )
                    if active_task:
                        _est, _clean, _ = unpack_task_note(active_task.get("note") or "")
                        # งานเสร็จเมื่อครบรอบตาม est ใน note เท่านั้น (ไม่ผูกแค่ planned_rounds ในหน่วยความจำ)
                        if _cr >= max(1, int(_est)):
                            api_update_task(
                                active_task["id"],
                                status="done",
                                note=pack_task_note(_clean, _est, _est),
                            )
                        else:
                            api_update_task(
                                active_task["id"],
                                note=pack_task_note(_clean, _est, _cr),
                            )

                threading.Thread(target=_persist_work_round, daemon=True).start()
                _home_focus_state["started_at"] = None

                if active_task and _cr >= max(1, int(unpack_task_note(active_task.get("note") or "")[0])):
                    _home_focus_state["completed_rounds"] = 0
                    _home_active_task_id = None
                    _home_focus_state["mode"] = "work"
                elif _cr % max(1, user_data["rounds_before_long_break"]) == 0:
                    _home_focus_state["mode"] = "long_break"
                else:
                    _home_focus_state["mode"] = "short_break"
            else:
                # จบ break แล้วกลับเข้า work mode ปกติ
                _home_focus_state["mode"] = "work"

            _home_focus_state["cur_time"] = mode_seconds(_home_focus_state["mode"])

            refresh_main_content(page)

    def on_focus_play(e):
        if _home_focus_state["mode"] == "work":
            if not active_task or (active_task.get("status") == "done"):
                return
        if _home_focus_state["is_running"]:
            _home_focus_state["is_running"] = False
            _home_focus_state["is_paused"] = True
            page.update()
            return
        if _home_focus_state["started_at"] is None:
            _home_focus_state["started_at"] = datetime.now()
        _home_focus_state["is_running"] = True
        _home_focus_state["is_paused"] = False
        page.run_task(_focus_tick)
        page.update()

    def on_focus_skip(e):
        _home_focus_state["is_running"] = False
        _home_focus_state["is_paused"] = False
        # กดข้าม = ไปโหมดถัดไปตามแถบ 3 โหมด
        if _home_focus_state["mode"] == "work":
            _home_focus_state["mode"] = "short_break"
        elif _home_focus_state["mode"] == "short_break":
            _home_focus_state["mode"] = "long_break"
        else:
            _home_focus_state["mode"] = "work"
        _home_focus_state["cur_time"] = mode_seconds(_home_focus_state["mode"])
        refresh_main_content(page)

    def set_mode(mode: str):
        def _set(e):
            _home_focus_state["is_running"] = False
            _home_focus_state["is_paused"] = False
            _home_focus_state["mode"] = mode
            _home_focus_state["cur_time"] = mode_seconds(mode)
            refresh_main_content(page)
        return _set

    def mode_tab(label: str, mode: str):
        active = _home_focus_state["mode"] == mode
        return Container(
            Text(label, size=12, weight="bold", color="white" if active else DARK),
            padding=ft.padding.symmetric(8, 12),
            border_radius=10,
            bgcolor=CORAL if active else "#F3E2D7",
            on_click=set_mode(mode),
            ink=True,
        )

    mode_label = {
        "work": "Work",
        "short_break": "พักสั้น",
        "long_break": "พักยาว",
    }.get(_home_focus_state["mode"], "Work")
    mode_color = {"work": "#FFC08A", "short_break": "#BFE2AE", "long_break": "#FFD78A"}.get(_home_focus_state["mode"], "#FFC08A")
    mode_icon = {"work": icons.BOLT, "short_break": icons.BOLT, "long_break": icons.BOLT}.get(_home_focus_state["mode"], icons.BOLT)

    focus_title = active_task.get("title") if active_task else "ยังไม่ได้เลือกงาน"
    _, focus_sub, _ = unpack_task_note(active_task.get("note") or "") if active_task else (1, "", 0)
    play_label = "กำลังเล่น" if _home_focus_state["is_running"] else "เริ่มจับเวลา"

    focus_card = Container(
        Column(
            [
                Row(
                    [
                        Text("รอบปัจจุบัน", size=11, color=MID),
                        Container(
                            Row([Icon(mode_icon, color=CORAL, size=14), Text(mode_label, size=11, color=DARK)], spacing=6),
                            padding=ft.padding.symmetric(10, 6),
                            bgcolor="#F5DFD2",
                            border_radius=14,
                        ),
                    ],
                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                ),
                Row(
                    [
                        mode_tab("Pomodoro", "work"),
                        mode_tab("Short Break", "short_break"),
                        mode_tab("Long Break", "long_break"),
                    ],
                    spacing=8,
                    alignment=MainAxisAlignment.CENTER,
                ),
                Container(
                    content=Column(
                        [
                            Container(
                                Stack(
                                [
                                    # วงมะเขือเทศหลัก
                                    Container(
                                        width=200,
                                        height=200,
                                        border_radius=999,
                                        bgcolor="#FFF2EA",
                                        border=ft.border.all(10, "#F2B089"),
                                        shadow=ft.BoxShadow(
                                            blur_radius=10,
                                            color="rgba(232,98,74,0.12)",
                                            offset=ft.Offset(0, 3),
                                        ),
                                    ),
                                    timer_ring,
                                    # ใบมะเขือเทศแบบหลายชั้น (ให้ดูสมจริงขึ้น)
                                    # เงาใต้ใบ
                                    Container(width=72, height=20, bgcolor="rgba(36,106,44,0.35)", border_radius=12, top=30, left=64),
                                    # ก้านกลาง
                                    Container(width=8, height=34, bgcolor="#2E7D32", border_radius=4, top=4, left=96),
                                    # กลีบกลาง
                                    Container(width=30, height=18, bgcolor="#2F8E3F", border_radius=10, top=16, left=85),
                                    # กลีบซ้าย-ขวาหลัก
                                    Container(width=26, height=16, bgcolor="#3FA447", border_radius=10, top=20, left=66),
                                    Container(width=26, height=16, bgcolor="#3FA447", border_radius=10, top=20, right=66),
                                    # กลีบซ้าย-ขวาย่อย
                                    Container(width=20, height=14, bgcolor="#57B65A", border_radius=9, top=24, left=56),
                                    Container(width=20, height=14, bgcolor="#57B65A", border_radius=9, top=24, right=56),
                                    # ไฮไลต์บนใบ
                                    Container(width=10, height=5, bgcolor="rgba(255,255,255,0.35)", border_radius=4, top=22, left=92),
                                    Container(
                                        timer_text,
                                        alignment=ft.Alignment(0, 0),
                                        width=200,
                                        height=200,
                                    ),
                                ]
                                ),
                                width=210,
                                height=210,
                                alignment=ft.Alignment(0, 0),
                            ),
                            Text(
                            focus_title,
                            size=34 if len(focus_title) < 10 else 20,
                            weight="bold",
                            color=DARK,
                            text_align=TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                            Text(
                            focus_sub or "ติ๊กงานด้านล่างเพื่อเริ่มจับเวลา",
                            size=13,
                            color=MID,
                            text_align=TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                            Text(
                            f"รอบที่ {_home_focus_state['completed_rounds']} / {_home_focus_state['planned_rounds']}",
                            size=13,
                            color=CORAL,
                            weight="bold",
                            text_align=TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    alignment=ft.Alignment(0, 0),
                ),
                Row(
                    [
                        ElevatedButton(
                            play_label,
                            icon=(
                                icons.PAUSE
                                if _home_focus_state["is_running"]
                                else icons.PLAY_ARROW
                            ),
                            on_click=on_focus_play,
                            bgcolor=CORAL if active_task else "#B6A396",
                            color="white",
                            style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
                            width=170,
                            height=52,
                        ),
                        ElevatedButton(
                            "ข้าม",
                            icon=icons.SKIP_NEXT,
                            on_click=on_focus_skip,
                            bgcolor="#F1E1D6",
                            color=DARK,
                            style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
                            width=120,
                            height=52,
                        ),
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    spacing=8,
                ),
            ],
            spacing=10,
        ),
        padding=18,
        border_radius=22,
        gradient=LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#FFF7F1", "#FFEBDD"]),
        border=ft.border.all(1.2, "#F2D9C8"),
    )

    def refresh_home():
        refresh_main_content(page)

    def make_select(t_id):
        def on_click(e):
            global _home_active_task_id
            task_obj = next((x for x in today_tasks if x.get("id") == t_id), None)
            if task_obj and (task_obj.get("status") == "done"):
                return
            _home_active_task_id = None if _home_active_task_id == t_id else t_id
            refresh_home()
        return on_click

    def make_del(t_id):
        def on_click(e):
            api_delete_task(t_id); refresh_home()
        return on_click

    def _render_task_items(tasks: list) -> list:
        items = []
        remaining = [t for t in tasks if (t.get("status") or "") != "done"]
        done_items = [t for t in tasks if (t.get("status") or "") == "done"]

        for t in (remaining + done_items):
            est, note_clean, act = unpack_task_note(t.get("note") or "")
            left = max(0, est - act)
            is_done = (t.get("status") or "") == "done"
            is_selected = t.get("id") == _home_active_task_id
            # ช่องซ้าย: เสร็จจริง = ติ๊กขาวบนเขียว | เลือกอยู่ = ติ๊กส้ม | ยังไม่เลือก = ว่าง
            if is_done:
                mark_bg, mark_bd, mark_icon = SAGE, SAGE, Icon(icons.CHECK, size=14, color="white")
            elif is_selected:
                mark_bg, mark_bd, mark_icon = PEACH_P, CORAL, Icon(icons.CHECK, size=14, color=CORAL)
            else:
                mark_bg, mark_bd, mark_icon = "#E7E0DA", "#E7E0DA", None
            title_color = "#6FA760" if is_done else (CORAL if is_selected else DARK)
            sub_color = "#6FA760" if is_done else (CORAL if is_selected else SOFT)
            items.append(
                Container(
                    Row(
                        [
                            Container(
                                content=mark_icon,
                                width=32,
                                height=32,
                                border_radius=8,
                                bgcolor=mark_bg,
                                border=ft.border.all(1, mark_bd),
                                alignment=ft.Alignment(0, 0),
                                ignore_interactions=True,
                            ),
                            Column(
                                [
                                    Text(
                                        t.get("title") or "-",
                                        size=14,
                                        weight="bold",
                                        color=title_color,
                                        style=ft.TextStyle(
                                            decoration=ft.TextDecoration.LINE_THROUGH if is_done else ft.TextDecoration.NONE
                                        ),
                                    ),
                                    Text(
                                        note_clean or "ไม่มีคำอธิบาย",
                                        size=11,
                                        color=sub_color,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS
                                    ),
                                    Row(
                                        [
                                            Container(
                                                Text(f"{act} / {est}", size=10, color="#9B4A2A"),
                                                bgcolor="#FFE3D2",
                                                border_radius=10,
                                                padding=ft.padding.symmetric(4, 8),
                                            ),
                                            Text(
                                                "เสร็จแล้ว" if is_done else (f"เหลือ {left} รอบ" if left else "ครบแล้ว"),
                                                size=10,
                                                color=MID,
                                            ),
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                expand=True,
                                spacing=4,
                            ),
                            IconButton(
                                icons.DELETE_OUTLINE,
                                icon_color=CORAL,
                                on_click=make_del(t["id"]),
                                disabled=is_done
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                    padding=12,
                    border_radius=14,
                    bgcolor=CARD,
                    border=ft.border.all(2 if is_selected else 1, CORAL if is_selected else LINE),
                    on_click=make_select(t["id"]) if not is_done else None,
                    ink=True,
                )
            )
        return items

    task_cards = _render_task_items(today_tasks)

    empty_state = Container(
        Column([
            Icon(icons.CELEBRATION, size=36, color="#BBB"),
            Text("ยังไม่มีงานในวันนี้", size=13, color="#999",
                 text_align=TextAlign.CENTER),
            Text(f"ผู้ใช้ ID #{uid} • กดปุ่ม + เพื่อเพิ่มงาน", size=11, color="#BBB",
                 text_align=TextAlign.CENTER),
        ], alignment=MainAxisAlignment.CENTER,
           horizontal_alignment=CrossAxisAlignment.CENTER, spacing=4),
        padding=28, bgcolor=PEACH_P, border_radius=16,
        alignment=ft.Alignment(0, 0),
    )

    # แยกรายการงานเป็น ListView เฉพาะ เพื่อให้เรนเดอร์/สกอลได้เสถียรบน Desktop
    tasks_list = ListView(
        controls=(task_cards if task_cards else [empty_state]),
        spacing=10,
        padding=0,
        expand=True,
        scroll=ScrollMode.AUTO,
    )

    remaining_tasks = [t for t in today_tasks if (t.get("status") or "") != "done"]
    total_est = 0
    total_act = 0
    remaining_pomo_count = 0
    for t in remaining_tasks:
        e, _, a = unpack_task_note(t.get("note") or "")
        total_est += e
        total_act += a
        remaining_pomo_count += max(0, e - a)
    total_minutes = total_chain_minutes_for_pomodoros(
        remaining_pomo_count,
        user_data["work_minutes"],
        user_data["short_break_minutes"],
        user_data["long_break_minutes"],
        user_data["rounds_before_long_break"],
    )
    finish_at = (
        (datetime.now() + timedelta(minutes=total_minutes)).strftime("%H:%M")
        if remaining_pomo_count > 0
        else "--:--"
    )

    task_section = Column(
        [
            Row([
                Text("งานวันนี้", size=16, weight="bold", color=DARK),
                Text(f"เหลือ {len(remaining_tasks)} งาน", size=12, color="#999"),
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            Container(
                content=tasks_list,
                height=420,
                border_radius=16,
                border=ft.border.all(1, LINE),
                bgcolor=CARD,
                padding=10,
            ),
            Container(
                Row(
                    [
                        Text(f"Pomos: {total_act} / {total_est}", size=13, color=DARK, weight="bold"),
                        Text(f"Finish At {finish_at}", size=13, color=CORAL, weight="bold"),
                    ],
                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.padding.symmetric(14, 16),
                border_radius=14,
                bgcolor="#F7DED0",
            ),
        ],
        spacing=10,
    )

    # ✅ music card: กดแล้วเล่นเพลงจริง
    def on_music_card_click(e):
        track_name = user_data.get("selected_music_track", DEFAULT_MUSIC_TRACK)
        play_audio(page, track_name)

    music_card = Container(
        Row([
            Container(
                Icon(icons.MUSIC_NOTE, size=26, color="white"),
                width=48,
                height=48,
                bgcolor="#C04A35",
                border_radius=12,
                alignment=ft.Alignment(0, 0),
            ),
            Column([
                Text(user_data.get("selected_music_track", DEFAULT_MUSIC_TRACK),
                     size=13, weight="bold", color="white"),
                Text("กำลังเล่น • กดเพื่อเปลี่ยน", size=10, color="#FFD6C2"),
            ], expand=True, spacing=2),
            Icon(icons.PLAY_CIRCLE_FILLED, color="white", size=32),
        ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(16, 20),
        bgcolor=CORAL, border_radius=18,
        shadow=ft.BoxShadow(blur_radius=12, color=SHADOW, offset=ft.Offset(0, 4)),
        on_click=on_music_card_click,
        ink=True,
    )

    return ListView(
        [focus_card, stats_row, task_section, music_card],
        spacing=18, padding=18, expand=True,
        scroll=ScrollMode.AUTO,
    )

# ==================== TASK TAB ====================
def task_tab(page: Page):
    def refresh():
        refresh_main_content(page)

    fab = Container(
        content=ft.FloatingActionButton(
            icon=icons.ADD, bgcolor=CORAL, foreground_color="white",
            on_click=lambda e: show_add_task_dialog(page, refresh),
        ),
        right=20,
        bottom=20,
    )
    # วาง FAB แบบ positioned เพื่อไม่ให้มี layer โปร่งใสทับทั้งหน้า
    return Stack([home_screen(page), fab], expand=True)


def refresh_main_content(page: Page):
    """Rebuild เนื้อหาตามแท็บที่เลือกอยู่ (ไม่บังคับกลับหน้าหลักเมื่อจับเวลา)"""
    items = getattr(page, "_nav_items", None)
    sel = getattr(page, "_nav_selected", None)
    mc = getattr(page, "_main_content", None)
    if items is not None and sel is not None and mc is not None:
        mc.content = items[sel[0]]["builder"](page)
    elif mc is not None:
        mc.content = task_tab(page)
    page.update()


# ==================== CALENDAR SCREEN ====================
def calendar_screen(page: Page):
    today     = datetime.now()
    all_tasks = api_get_all_tasks(current_user["id"])

    view_year  = [today.year]
    view_month = [today.month]

    task_list_col = Column([], spacing=8, scroll=ScrollMode.AUTO)

    def render_tasks_for(day_str: str):
        day_tasks = [t for t in all_tasks if (t.get("date") or "")[:10] == day_str]
        task_list_col.controls.clear()
        task_list_col.controls.append(
            Container(
                Row([
                    Icon(icons.EVENT, color=CORAL, size=16),
                    Text(f"งานวันที่ {day_str}  ({len(day_tasks)} งาน)",
                         size=14, weight="bold", color=DARK),
                ], spacing=6),
                padding=ft.padding.only(bottom=6),
            )
        )
        if day_tasks:
            for t in day_tasks:
                sc = get_status_color(t["status"])
                task_list_col.controls.append(Container(
                    Row([
                        Container(width=5, bgcolor=sc, border_radius=4, height=52),
                        Column([
                            Text(t["title"], size=13, weight="bold", color=DARK),
                            Row([
                                Container(
                                    Text(get_status_text(t["status"]),
                                         size=9, color="white"),
                                    bgcolor=sc,
                                    padding=ft.padding.symmetric(3, 8), border_radius=10,
                                ),
                                Text(t.get("note","") or "", size=10, color=SOFT,
                                     overflow=ft.TextOverflow.ELLIPSIS, expand=True)
                                if t.get("note") else Container(),
                            ], spacing=6),
                        ], expand=True, spacing=4),
                    ], spacing=10),
                    padding=12, bgcolor=CARD, border_radius=14,
                    border=ft.border.all(1, LINE),
                    shadow=ft.BoxShadow(blur_radius=6, color=SHADOW, offset=ft.Offset(0,2)),
                ))
        else:
            task_list_col.controls.append(
                Container(
                    Text("ไม่มีงานในวันนี้", size=12, color="#AAA",
                         text_align=TextAlign.CENTER),
                    padding=20, bgcolor=PEACH_P, border_radius=12,
                    alignment=ft.Alignment(0, 0),
                )
            )
        page.update()

    grid_col = Column([], spacing=4)

    def build_grid():
        grid_col.controls.clear()
        y, m = view_year[0], view_month[0]

        grid_col.controls.append(Row(
            [Text(d, size=11, weight="bold", color=SOFT,
                  text_align=TextAlign.CENTER, width=46)
             for d in ["อา","จ","อ","พ","พฤ","ศ","ส"]],
            spacing=4,
        ))

        first_day = datetime(y, m, 1)
        if m == 12:
            last_day = datetime(y+1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(y, m+1, 1) - timedelta(days=1)

        offset = (first_day.weekday() + 1) % 7
        days: list = [None] * offset
        days += [datetime(y, m, d) for d in range(1, last_day.day + 1)]

        week_row = []
        for day in days:
            if day is None:
                week_row.append(Container(width=46, height=56))
            else:
                is_today = (day.year == today.year and
                            day.month == today.month and
                            day.day == today.day)
                ds = day.strftime("%Y-%m-%d")
                dots = []
                for t in all_tasks:
                    if (t.get("date") or "")[:10] == ds:
                        dots.append(Container(width=5, height=5,
                                              bgcolor=get_status_color(t["status"]),
                                              border_radius=3))
                    if len(dots) >= 3:
                        break

                def day_click(e, s=ds):
                    render_tasks_for(s)

                week_row.append(Container(
                    Column([
                        Text(str(day.day), size=13, weight="bold",
                             color="white" if is_today else DARK),
                        Row(dots, spacing=2) if dots else Container(height=5),
                    ], alignment=MainAxisAlignment.CENTER,
                       horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
                    width=46, height=56,
                    bgcolor=CORAL if is_today else CARD,
                    border_radius=10,
                    border=ft.border.all(1.5, CORAL if is_today else LINE),
                    on_click=day_click,
                    ink=True,
                ))
            if len(week_row) == 7:
                grid_col.controls.append(Row(week_row, spacing=4))
                week_row = []
        if week_row:
            while len(week_row) < 7:
                week_row.append(Container(width=46, height=56))
            grid_col.controls.append(Row(week_row, spacing=4))

    build_grid()
    render_tasks_for(today.strftime("%Y-%m-%d"))

    month_title = Text(
        f"{get_thai_month_name(view_month[0])} {view_year[0] + 543}",
        size=18, weight="bold", color=DARK,
    )

    def prev_month(e):
        if view_month[0] == 1: view_month[0] = 12; view_year[0] -= 1
        else: view_month[0] -= 1
        month_title.value = f"{get_thai_month_name(view_month[0])} {view_year[0] + 543}"
        build_grid(); page.update()

    def next_month(e):
        if view_month[0] == 12: view_month[0] = 1; view_year[0] += 1
        else: view_month[0] += 1
        month_title.value = f"{get_thai_month_name(view_month[0])} {view_year[0] + 543}"
        build_grid(); page.update()

    nav_row = Row([
        IconButton(icons.CHEVRON_LEFT, on_click=prev_month, icon_color=DARK),
        month_title,
        IconButton(icons.CHEVRON_RIGHT, on_click=next_month, icon_color=DARK),
    ], alignment=MainAxisAlignment.CENTER, vertical_alignment=CrossAxisAlignment.CENTER)

    return Column([
        Container(nav_row, padding=ft.padding.symmetric(8, 16)),
        Container(grid_col, padding=ft.padding.symmetric(0, 16)),
        Divider(height=1, color=LINE),
        Container(task_list_col, padding=ft.padding.symmetric(12, 16), expand=True),
    ], spacing=0, expand=True, scroll=ScrollMode.AUTO)

# ==================== TIMER SCREEN ====================
def timer_screen(page: Page, on_close=None, embedded: bool = False):
    user_data = get_user_data()
    uid       = current_user["id"]

    WORK_S  = user_data["work_minutes"] * 60
    SHORT_S = user_data["short_break_minutes"] * 60
    LONG_S  = user_data["long_break_minutes"] * 60
    ROUNDS  = user_data["rounds_before_long_break"]

    # --- ดึงงานที่ยังไม่เสร็จ ---
    today_tasks = api_get_tasks_by_date(uid, get_today_date())
    todo_tasks = [t for t in today_tasks if t["status"] != "done"]
   



    def on_add_task(e):
        show_add_task_dialog(page, lambda: page.update())

    add_task_btn = ft.ElevatedButton(
        " เพิ่มงาน", icon=icons.ADD, bgcolor=PEACH, color=DARK,
        on_click=on_add_task, width=140, height=40,
        style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    cur_time   = [WORK_S]
    total_time = [WORK_S]
    is_running = [False]
    is_paused  = [False]
    cur_round  = [1]
    stype      = ["work"]
    started_at = [None]

    def fmt(sec):
        return f"{sec//60:02d}:{sec%60:02d}"

    time_text  = Text(fmt(WORK_S), size=56, weight="bold", color="white")
    round_text = Text(f"รอบที่ {cur_round[0]} / {ROUNDS}", size=12, color="#CCC")
    stype_text  = Text("Work", size=14, color=PEACH)
    ring       = ProgressRing(value=1.0, width=230, height=230,
                               stroke_width=16, color=PEACH)

    play_btn = ft.ElevatedButton(
        "เริ่มจับเวลา",
        icon=icons.PLAY_ARROW,
        bgcolor=CORAL,
        color="white",
        width=170,
        height=54,
        style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=16)),
    )

    def save_session(completed: bool):
        if started_at[0] is None:
            return
        elapsed_sec = total_time[0] - cur_time[0]
        # ถ้าจบรอบจริง ให้เก็บ "เวลารอบเต็ม" ตามโหมดที่ใช้งานจริง
        # เช่น short_break = 5, long_break = 15 (จาก settings ผู้ใช้)
        if completed:
            mins = max(1, total_time[0] // 60)
        else:
            # break ให้เก็บตามโหมดจริงเสมอ (ไม่ให้กลายเป็น 1 นาที)
            if stype[0] in ("short_break", "long_break"):
                mins = max(1, total_time[0] // 60)
            else:
                # work ที่หยุดกลางทาง เก็บตามเวลาที่ใช้จริง
                mins = max(1, elapsed_sec // 60)
        # ผูก session กับงานที่กำลังเลือกอยู่ให้มากที่สุด (กัน task_id เป็น NULL)
        task_id = None
        try:
            # 1) ใช้งานที่เลือกจากหน้าหลักก่อน
            task_id = _home_active_task_id
            # 2) ถ้ายังไม่มี ให้ fallback งานแรกที่ยังไม่ done ของวันนี้
            if task_id is None and todo_tasks:
                task_id = todo_tasks[0].get("id")
        except Exception:
            task_id = None
        threading.Thread(
            target=api_create_session,
            args=(uid, task_id, stype[0], mins,
                  started_at[0], datetime.now(), completed),
            daemon=True,
        ).start()

    async def _tick_loop():
        while is_running[0] and cur_time[0] > 0:
            await asyncio.sleep(1)
            if not is_running[0]:
                break
            cur_time[0]     -= 1
            ring.value       = cur_time[0] / total_time[0]
            time_text.value  = fmt(cur_time[0])
            ring.update()
            time_text.update()

        if is_running[0] and cur_time[0] == 0:
            is_running[0]    = False
            is_paused[0]     = False
            save_session(True)
            time_text.value  = "เสร็จสิ้น!"
            play_btn.content = "เริ่มจับเวลา"
            play_btn.icon = icons.PLAY_ARROW
            play_btn.bgcolor = CORAL
            started_at[0]    = None
            time_text.update()
            play_btn.update()

    def on_play(e):
        # 3-state: stopped -> running -> paused -> running ...
        if is_running[0]:
            # pause
            is_running[0] = False
            is_paused[0]  = True
            play_btn.content = "หยุดการจับเวลา"
            play_btn.icon = icons.PLAY_ARROW
            play_btn.bgcolor = CORAL
            play_btn.update()
            return

        # not running: either resume paused or start new
        if is_paused[0]:
            is_running[0] = True
            is_paused[0]  = False
            play_btn.content = "กำลังเล่น"
            play_btn.icon = icons.PAUSE
            play_btn.bgcolor = "#C04A35"
            play_btn.update()
            page.run_task(_tick_loop)
            return

        # start new
        if cur_time[0] == 0:
            cur_time[0]     = total_time[0]
            ring.value      = 1.0
            time_text.value = fmt(cur_time[0])

        is_running[0]    = True
        is_paused[0]     = False
        started_at[0]    = datetime.now()
        play_btn.content = "กำลังเล่น"
        play_btn.icon = icons.PAUSE
        play_btn.bgcolor = "#C04A35"
        play_btn.update()
        page.run_task(_tick_loop)

    play_btn.on_click = on_play

    def on_reset(e):
        is_running[0] = False
        is_paused[0]  = False
        if started_at[0]:
            save_session(False)
        started_at[0]    = None
        cur_time[0]      = total_time[0]
        ring.value       = 1.0
        time_text.value  = fmt(cur_time[0])
        play_btn.content = "เริ่มจับเวลา"
        play_btn.icon = icons.PLAY_ARROW
        play_btn.bgcolor = CORAL
        page.update()

    def on_skip(e):
        is_running[0] = False
        is_paused[0]  = False
        if started_at[0]:
            save_session(False)
        started_at[0]    = None
        play_btn.content = "เริ่มจับเวลา"
        play_btn.icon = icons.PLAY_ARROW
        play_btn.bgcolor = CORAL

        if stype[0] == "work":
            cur_round[0] += 1
            if cur_round[0] > ROUNDS:
                cur_round[0] = 1
                _switch("long_break")
            else:
                _switch("short_break")
        else:
            _switch("work")

        round_text.value = f"รอบที่ {cur_round[0]} / {ROUNDS}"
        page.update()

    # เก็บ reference แท็บเพื่ออัปเดตสีหลังกด (ไม่ใช่แค่ค่าเริ่มต้นตอนสร้างครั้งเดียว)
    session_tab_items = []

    def refresh_session_tabs():
        for item in session_tab_items:
            key = item["key"]
            color = item["color"]
            cont = item["container"]
            txt = item["text"]
            ic = item["icon"]
            active = stype[0] == key
            cont.bgcolor = color if active else "rgba(255,255,255,0.12)"
            col = "white" if active else "rgba(255,255,255,0.7)"
            txt.color = col
            ic.color = col

    def _switch(s):
        stype[0] = s
        if s == "work":
            total_time[0] = WORK_S
            ring.color = PEACH
            stype_text.value = "Work"
        elif s == "short_break":
            total_time[0] = SHORT_S
            ring.color = SAGE
            stype_text.value = "พักสั้น"
        else:
            total_time[0] = LONG_S
            ring.color = AMBER
            stype_text.value = "พักยาว"
        cur_time[0]     = total_time[0]
        time_text.value = fmt(cur_time[0])
        ring.value      = 1.0
        refresh_session_tabs()

    def make_tab(label, key, color, tab_icon):
        active = stype[0] == key
        col = "white" if active else "rgba(255,255,255,0.7)"
        ic = Icon(tab_icon, size=14, color=col)
        txt = Text(label, size=12, weight="bold", color=col)
        row = Row(
            [ic, txt],
            spacing=4,
            tight=True,
            alignment=MainAxisAlignment.CENTER,
        )

        def on_click(e):
            if is_running[0]:
                return
            _switch(key)
            play_btn.content = "เริ่มจับเวลา"
            play_btn.icon = icons.PLAY_ARROW
            play_btn.bgcolor = CORAL
            started_at[0]    = None
            is_paused[0]     = False
            page.update()

        cont = Container(
            row,
            padding=ft.padding.symmetric(10, 16),
            bgcolor=color if stype[0] == key else "rgba(255,255,255,0.12)",
            border_radius=12,
            on_click=on_click,
            ink=True,
        )
        session_tab_items.append(
            {
                "key": key,
                "color": color,
                "container": cont,
                "text": txt,
                "icon": ic,
            }
        )
        return cont

    session_tabs = Row(
        [
            make_tab("Work", "work", PEACH, icons.BOLT),
            make_tab("พักสั้น", "short_break", SAGE, icons.LOCAL_CAFE),
            make_tab("พักยาว", "long_break", AMBER, icons.PARK),
        ],
        spacing=8,
        alignment=MainAxisAlignment.CENTER,
    )
    refresh_session_tabs()

    ring_widget = Container(
        Stack([
            ring,
            Column([time_text, stype_text, round_text],
                   alignment=MainAxisAlignment.CENTER,
                   horizontal_alignment=CrossAxisAlignment.CENTER, spacing=6),
        ], alignment=ft.Alignment(0, 0)),
        alignment=ft.Alignment(0, 0),
        height=250,
    )

    controls = Row([
        ft.TextButton(
            "รีเซ็ต",
            icon=icons.REFRESH,
            style=ButtonStyle(color="white"),
            on_click=on_reset,
        ),
        play_btn,
        ft.TextButton(
            "ข้าม",
            icon=icons.SKIP_NEXT,
            style=ButtonStyle(color="white"),
            on_click=on_skip,
        ),
    ], alignment=MainAxisAlignment.CENTER, spacing=12)

    # --- เพิ่ม dropdown เลือกงานและปุ่มเพิ่มงานใต้ timer ---
    task_row = Row([
      add_task_btn
    ], alignment=MainAxisAlignment.CENTER, spacing=12)

    body = Column(
        [
            Container(height=8),
            Row(
                [
                    Icon(icons.TIMER, color="white", size=22),
                    Text("Pomo Focus", weight="bold", color="white", size=20),
                ],
                spacing=8,
                alignment=MainAxisAlignment.CENTER,
            ),
            Container(height=8),
            task_row,
            session_tabs,
            ring_widget,
            controls,
        ],
        spacing=20,
        horizontal_alignment=CrossAxisAlignment.CENTER,
    )

    if embedded:
        return body

    return Container(
        body,
        expand=True,
        gradient=LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                                colors=[CORAL, "#C04A35", "#3D1A10"]),
    )

# ==================== MUSIC SCREEN (FIXED) ====================
def music_screen(page: Page):
    _load_music_durations_from_files()
    user_data = get_user_data()
    global _selected_track_name
    global _music_category_filter
    now_playing = _selected_track_name or user_data.get("selected_music_track", "ไม่ได้เลือกเพลง")

    def _is_any_audio_loaded() -> bool:
        # มีตัวเล่น/ไฟล์ถูกโหลดอยู่ (อาจกำลัง pause)
        return (_current_audio_control is not None) or (_pygame_current_path is not None)

    def _is_any_audio_playing() -> bool:
        # กำลังเล่นจริง (ไม่ใช่ pause)
        if _current_audio_control is not None and not _audio_paused:
            return True
        if _pygame_current_path is not None and not _pygame_paused:
            return True
        return False

    def _is_any_audio_paused() -> bool:
        return (_audio_paused and _current_audio_control is not None) or (_pygame_paused and _pygame_current_path is not None)

    def _has_selected_track() -> bool:
        return bool(now_playing and now_playing != "ไม่ได้เลือกเพลง")

    def play_local_audio(track: dict):
        """
        เล่นเพลง (pygame บน Windows ก่อน, ไม่งั้น flet-audio)
        - คลิกเพลงเดิมที่กำลังเล่น → pause
        - คลิกเพลงเดิมตอนพัก → resume
        - คลิกเพลงอื่น → เริ่มเล่น (จบแล้วไปเพลงถัดไปในรายการอัตโนมัติ)
        """
        global _user_cache

        track_name = track["name"]

        if track_name == now_playing and _is_any_audio_playing():
            pause_current_audio(page)
            refresh_main_content(page)
            return
        if track_name == now_playing and _is_any_audio_paused():
            resume_current_audio(page)
            refresh_main_content(page)
            return

        if _audio_disabled:
            return

        if not AUDIO_FILES.get(track_name):
            print(f"⚠️  ไม่พบไฟล์: {track_name} ใน AUDIO_FILES")
            return

        _play_music_track(page, track_name, user_started=True)

        if _user_cache:
            _user_cache["selected_music_track"] = track_name

        refresh_main_content(page)

    # UI ────────────────────────────────────────────────

    # แยกเพลงตามหมวดหมู่ (category)
    tracks_to_show = [
        t for t in my_tracks
        if _music_category_filter == "ทั้งหมด" or t.get("category") == _music_category_filter
    ]

    # ใช้ Text object อ้างอิงเพื่ออัปเดตเวลาแบบ real-time
    duration_texts = {}

    def _total_label_for(name: str) -> str:
        sec = _track_total_duration_sec.get(name)
        return _sec_to_mmss(sec) if sec is not None else "--:--"

    current_track_name = _selected_track_name or user_data.get("selected_music_track", DEFAULT_MUSIC_TRACK)

    track_rows = []
    for t in tracks_to_show:
        is_sel = t["name"] == now_playing
        is_active = is_sel and _is_any_audio_playing()
        is_paused_sel = is_sel and _is_any_audio_paused()

        if is_active:
            track_mark = Icon(icons.PAUSE, size=16, color="white")
        elif is_sel or is_paused_sel:
            track_mark = Icon(icons.PLAY_ARROW, size=16, color="white")
        else:
            track_mark = Text(
                str(t["id"]),
                size=12,
                color="white",
                text_align=TextAlign.CENTER,
            )

        # ถ้าแถวนี้คือเพลงที่กำลังเล่น ให้เริ่มด้วย "elapsed / total"
        total = _track_total_duration_sec.get(t["name"])
        elapsed = _get_music_elapsed_sec() if t["name"] == current_track_name else None
        if t["name"] == current_track_name:
            elapsed_disp = elapsed
            if total is not None and elapsed is not None:
                # กันเคส elapsed ล้ำเลยตอนเพลงจบ (ยังไม่สลับเพลงเร็วพอ)
                elapsed_disp = min(float(elapsed), float(total))
            total_text = _sec_to_mmss(total) if total is not None else "--:--"
            dur_txt = Text(f"{_sec_to_mmss(elapsed_disp)} / {total_text}", size=11, color=SOFT)
        else:
            dur_txt = Text(_total_label_for(t["name"]), size=11, color=SOFT)
        duration_texts[t["name"]] = dur_txt

        track_rows.append(Container(
            Row([
                Container(
                    track_mark,
                    width=36,
                    height=36,
                    bgcolor=t["icon_color"],
                    border_radius=10,
                    alignment=ft.Alignment(0, 0),
                ),
                Column([
                    Text(t["name"], size=13, weight="bold", color=DARK),
                    Text(t["category"], size=10, color=SOFT),
                ], expand=True, spacing=2),
                dur_txt,
            ], spacing=12),
            padding=14,
            bgcolor=PEACH_P if is_sel else CARD,
            border_radius=14,
            border=ft.border.all(1.5, CORAL if is_active else LINE),
            on_click=lambda e, trk=t: play_local_audio(trk),
            ink=True,
        ))

    # ==================== Category Tabs ====================
    def _set_category(cat_key: str):
        def _on_click(e):
            global _music_category_filter
            _music_category_filter = cat_key
            refresh_main_content(page)
        return _on_click

    tab_defs = [
        ("เพลงทั้งหมด", "ทั้งหมด"),
        ("เพลงละครฟังสบาย", "เพลงละครฟังสบาย"),
        ("เพลงแจ๊สเพราะๆ", "เพลงแจ๊สเพราะๆ"),
        ("เพลงชิลฟีลคาเฟ่", "เพลงชิลฟีลคาเฟ่"),
    ]

    category_tabs = Row(
        [
            Container(
                Text(lbl,
                     size=12, weight="bold",
                     color="white" if _music_category_filter == key else "rgba(255,255,255,0.75)"),
                padding=ft.padding.symmetric(10, 14),
                border_radius=12,
                bgcolor=CORAL if _music_category_filter == key else "rgba(255,255,255,0.12)",
                on_click=_set_category(key),
                ink=True,
            )
            for (lbl, key) in tab_defs
        ],
        spacing=8,
        alignment=MainAxisAlignment.CENTER,
    )

    # อัปเดตเวลา elapsed / duration เฉพาะตอนที่อยู่หน้า “เพลง”
    global _music_elapsed_tick_token
    _music_elapsed_tick_token += 1
    tick_token = _music_elapsed_tick_token
    music_tab_idx = None
    try:
        items = getattr(page, "_nav_items", None)
        sel = getattr(page, "_nav_selected", None)
        if items is not None:
            for i, it in enumerate(items):
                if it.get("label") == "เพลง":
                    music_tab_idx = i
                    break
    except Exception:
        music_tab_idx = None

    def _is_music_tab_selected() -> bool:
        try:
            if music_tab_idx is None:
                return True
            return getattr(page, "_nav_selected", [0])[0] == music_tab_idx
        except Exception:
            return False

    async def _music_elapsed_tick():
        while _music_elapsed_tick_token == tick_token and _is_music_tab_selected():
            try:
                current = _selected_track_name or user_data.get("selected_music_track", DEFAULT_MUSIC_TRACK)
                elapsed = _get_music_elapsed_sec()

                # Fallback: ถ้า elapsed เกินความยาวเพลงแล้ว แต่ยังไม่สลับเพลง ให้สั่งเลื่อนไปเพลงถัดไป
                # (กันกรณี watcher/COMPLETED event ทำงานช้า)
                current_total = _track_total_duration_sec.get(current)
                if (
                    current_total is not None
                    and elapsed >= float(current_total) - 0.15
                    and (not _music_chain_advancing)
                    and (not _music_user_stopped_chain)
                ):
                    _schedule_music_track_advance()

                # อัปเดตเฉพาะตัวอักษรเวลา (ไม่ต้อง rebuild ทั้งหน้า)
                for name, txt in duration_texts.items():
                    total = _track_total_duration_sec.get(name)
                    if name == current:
                        total_text = _sec_to_mmss(total) if total is not None else "--:--"
                        elapsed_disp = elapsed
                        if total is not None:
                            elapsed_disp = min(float(elapsed), float(total))
                        txt.value = f"{_sec_to_mmss(elapsed_disp)} / {total_text}"
                    else:
                        txt.value = _total_label_for(name)

                page.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    try:
        # ใช้รูปแบบเดียวกับ timer หลักของแอป เพื่อให้ loop วิ่งต่อเนื่องจริง
        page.run_task(_music_elapsed_tick)
    except Exception:
        pass

    def _find_track_by_name(name: str):
        for t in my_tracks:
            if t.get("name") == name:
                return t
        return None

    # ✅ แถบ Now Playing แสดงปุ่มพัก/เล่นต่อ (ต่อจากเดิม)
    def on_pause(e):
        pause_current_audio(page)
        refresh_main_content(page)

    def on_resume(e):
        trk = _find_track_by_name(now_playing)
        if trk:
            # ถ้าเคย pause ไว้ ให้ resume ต่อจากเดิม
            if _pygame_paused or _audio_paused:
                resume_current_audio(page)
            else:
                play_local_audio(trk)
            refresh_main_content(page)

    def on_stop_music(e):
        stop_music_playback(page)
        refresh_main_content(page)

    now_playing_bar = Container(
        Row([
            Container(
                Icon(
                    icons.PAUSE_CIRCLE_FILLED if _is_any_audio_playing() else (icons.PLAY_CIRCLE_FILLED if _is_any_audio_paused() else icons.MUSIC_VIDEO),
                    color="white"
                ),
                width=64, height=64, bgcolor=CORAL, border_radius=16,
                alignment=ft.Alignment(0, 0),
            ),
            Column([
                Text(
                    "กำลังเล่นปัจจุบัน"
                    if _is_any_audio_playing()
                    else ("พักอยู่" if _is_any_audio_paused() else ("หยุดอยู่" if _has_selected_track() else "ยังไม่ได้เล่น")),
                     size=11, color=SOFT),
                Text(
                    now_playing
                    if (_is_any_audio_loaded() or _has_selected_track())
                    else "กดเพลงด้านล่างเพื่อเล่น",
                     size=16, weight="bold", color=DARK),
            ], spacing=4, expand=True),
            # ✅ ปุ่มเล่นต่อ: แสดงตอน "หยุดอยู่" แต่มีเพลงที่เลือกแล้ว
            IconButton(
                icons.PLAY_CIRCLE_FILLED,
                icon_color=CORAL,
                icon_size=36,
                on_click=on_resume,
                visible=_is_any_audio_paused() or ((not _is_any_audio_loaded()) and _has_selected_track()),
            ),
            # ✅ ปุ่ม Pause จะแสดงเฉพาะตอนมีเพลงเล่น (รวม pygame)
            IconButton(
                icons.PAUSE_CIRCLE,
                icon_color=CORAL,
                icon_size=36,
                on_click=on_pause,
                visible=_is_any_audio_playing(),
            ),
            IconButton(
                icons.STOP_CIRCLE,
                icon_color=CORAL,
                icon_size=36,
                tooltip="หยุดและปิดการเล่นต่อคิว",
                on_click=on_stop_music,
                visible=_is_any_audio_loaded() or _is_any_audio_playing() or _is_any_audio_paused(),
            ),
        ], spacing=14),
        padding=18, bgcolor=PEACH_P, border_radius=20,
    )

    return ListView([
        Container(height=10),
        Row([
            Icon(icons.MUSIC_NOTE, color=CORAL),
            Text("คลังเพลงส่วนตัว", size=20, weight="bold", color=DARK),
        ], spacing=8),
        now_playing_bar,
        Divider(height=16, color=LINE),
        category_tabs,
        Divider(height=16, color=LINE),
        *track_rows
    ], spacing=12, padding=18, expand=True)


# ==================== PROFILE SCREEN ====================
def profile_screen(page: Page):
    user_data = get_user_data()
    stats     = api_get_stats(current_user["id"])

    def refresh():
        refresh_main_content(page)

    hero = Container(
             Column([
            Container(
                Text(user_data["username"][0].upper(), size=44, weight="bold", color="white"),
                width=96, height=96, bgcolor=CORAL, border_radius=48,
                border=ft.border.all(3, "#F7E6DC"),
                alignment=ft.Alignment(0, 0),
            ),
            Text(user_data["username"], size=20, weight="bold", color=DARK),
        ], alignment=MainAxisAlignment.CENTER,
           horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
        padding=20,
    )

    def scard(label, value, color, title_icon=None):
        if title_icon is not None:
            title = Row(
                [
                    Icon(title_icon, size=13, color=color),
                    Text(label, size=11, color=DARK, text_align=TextAlign.CENTER),
                ],
                spacing=4,
                tight=True,
                alignment=MainAxisAlignment.CENTER,
            )
        else:
            title = Text(label, size=11, color=DARK, text_align=TextAlign.CENTER)
        return Card(
            Container(
                Column(
                    [
                        title,
                        Text(str(value), size=22, weight="bold", color=color),
                    ],
                    alignment=MainAxisAlignment.CENTER,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=14,
            ),
            expand=True,
        )

    stat_row = Row(
        [
            scard("รอบทั้งหมด", stats["total_sessions"], PEACH, icons.TIMER),
            scard("งานเสร็จ", stats["total_tasks_done"], SAGE, icons.CHECK_CIRCLE),
            scard("ชั่วโมง", f"{stats['total_focus_hours']}h", AMBER, icons.SCHEDULE),
        ],
        spacing=8,
    )

    def show_edit_profile_dialog(e):
        uname_field = TextField(
            label="ชื่อผู้ใช้", value=user_data["username"],
            bgcolor=PEACH_P, border_radius=12,
            text_style=ft.TextStyle(color=DARK),
            prefix_icon=icons.PERSON,
        )
        email_field = TextField(
            label="อีเมล", value=user_data["email"],
            bgcolor=PEACH_P, border_radius=12,
            text_style=ft.TextStyle(color=DARK),
            prefix_icon=icons.EMAIL,
            disabled=True,
        )
        msg = Text("", size=12, color=CORAL)
        dlg = AlertDialog(open=False)

        def on_save(ev):
            new_name  = uname_field.value.strip()
            if not new_name:
                msg.value = "กรุณากรอกชื่อผู้ใช้"
                page.update(); return

            result = api_update_profile(current_user["id"], username=new_name)
            if result and result.get("status") == "success":
                global _user_cache
                _user_cache = {}
                current_user["username"] = result["user"]["username"]
                msg.value = "บันทึกสำเร็จ"
                msg.color = SAGE
                page.update()
                import time as _t
                def close():
                    _t.sleep(0.8); dlg.open = False; page.update(); refresh()
                threading.Thread(target=close, daemon=True).start()
            else:
                err_msg = "ไม่สามารถบันทึกได้"
                if result and "detail" in result:
                    err_msg += f"\n{result['detail']}"
                msg.value = err_msg
                page.update()

        def on_cancel(ev):
            dlg.open = False; page.update()

        dlg.title = Row([
            Icon(icons.EDIT, color=CORAL, size=20),
            Text("แก้ไขโปรไฟล์", size=17, weight="bold", color=CORAL),
        ], spacing=8)
        dlg.content = Container(
            Column([uname_field, email_field, msg], spacing=12, tight=True),
            width=340, padding=ft.padding.only(top=8),
        )
        dlg.actions = [
            TextButton("ยกเลิก", on_click=on_cancel, style=ButtonStyle(color=SOFT)),
            ft.ElevatedButton(
                "บันทึก",
                icon=icons.SAVE,
                bgcolor=CORAL,
                color="white",
                on_click=on_save,
                style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            ),
        ]
        dlg.actions_alignment = MainAxisAlignment.END
        dlg.shape = ft.RoundedRectangleBorder(radius=20)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def show_change_password_dialog(e):
        old_field = TextField(
            label="รหัสผ่านเดิม", password=True, can_reveal_password=True,
            bgcolor=PEACH_P, border_radius=12,
            text_style=ft.TextStyle(color=DARK),
            prefix_icon=icons.LOCK,
        )
        new_field = TextField(
            label="รหัสผ่านใหม่", password=True, can_reveal_password=True,
            bgcolor=PEACH_P, border_radius=12,
            text_style=ft.TextStyle(color=DARK),
            prefix_icon=icons.LOCK_OPEN,
        )
        confirm_field = TextField(
            label="ยืนยันรหัสผ่านใหม่", password=True, can_reveal_password=True,
            bgcolor=PEACH_P, border_radius=12,
            text_style=ft.TextStyle(color=DARK),
            prefix_icon=icons.LOCK_OPEN,
        )
        msg = Text("", size=12, color=CORAL)
        dlg = AlertDialog(open=False)

        def on_save(ev):
            old_pw  = old_field.value.strip()
            new_pw  = new_field.value.strip()
            conf_pw = confirm_field.value.strip()
            if not old_pw or not new_pw or not conf_pw:
                msg.value = "กรุณากรอกข้อมูลให้ครบ"
                page.update(); return
            if new_pw != conf_pw:
                msg.value = "รหัสผ่านใหม่ไม่ตรงกัน"
                page.update(); return
            if len(new_pw) < 4:
                msg.value = "รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร"
                page.update(); return

            result = api_change_password(current_user["id"], old_pw, new_pw)
            if result and result.get("status") == "success":
                msg.value = "เปลี่ยนรหัสผ่านสำเร็จ"
                msg.color = SAGE
                page.update()
                import time as _t
                def close():
                    _t.sleep(0.8); dlg.open = False; page.update()
                threading.Thread(target=close, daemon=True).start()
            else:
                msg.value = "รหัสผ่านเดิมไม่ถูกต้อง"
                page.update()

        def on_cancel(ev):
            dlg.open = False; page.update()

        dlg.title = Row([
            Icon(icons.LOCK_RESET, color=CORAL, size=20),
            Text("เปลี่ยนรหัสผ่าน", size=17, weight="bold", color=CORAL),
        ], spacing=8)
        dlg.content = Container(
            Column([old_field, new_field, confirm_field, msg], spacing=12, tight=True),
            width=340, padding=ft.padding.only(top=8),
        )
        dlg.actions = [
            TextButton("ยกเลิก", on_click=on_cancel, style=ButtonStyle(color=SOFT)),
            ft.ElevatedButton(
                "เปลี่ยนรหัส",
                icon=icons.LOCK,
                bgcolor=CORAL,
                color="white",
                on_click=on_save,
                style=ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
            ),
        ]
        dlg.actions_alignment = MainAxisAlignment.END
        dlg.shape = ft.RoundedRectangleBorder(radius=20)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def menu_row(icon_name, label, sublabel, on_click_fn):
        return Container(
            Row([
                Container(
                    Icon(icon_name, color=CORAL, size=22),
                    width=44, height=44, bgcolor=PEACH_P, border_radius=12,
                    alignment=ft.Alignment(0, 0),
                ),
                Column([
                    Text(label, size=14, weight="bold", color=DARK),
                    Text(sublabel, size=11, color=SOFT),
                ], expand=True, spacing=2),
                Icon(icons.CHEVRON_RIGHT, color=SOFT, size=20),
            ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
            padding=16, bgcolor=CARD, border_radius=16,
            border=ft.border.all(1, LINE),
            shadow=ft.BoxShadow(blur_radius=6, color=SHADOW, offset=ft.Offset(0, 2)),
            on_click=on_click_fn, ink=True,
        )

    edit_profile_row = menu_row(
        icons.EDIT, "แก้ไขโปรไฟล์", "เปลี่ยนชื่อและอีเมล",
        show_edit_profile_dialog,
    )
    change_pw_row = menu_row(
        icons.LOCK_RESET, "เปลี่ยนรหัสผ่าน", "อัปเดตความปลอดภัย",
        show_change_password_dialog,
    )

    def logout(e):
        global current_user, _user_cache
        stop_music_playback(page)
        current_user = {}; _user_cache = {}
        build_app(page)

    logout_btn = Container(
        Row([
            Icon(icons.LOGOUT, color=CORAL),
            Text("ออกจากระบบ", size=14, weight="bold", color=CORAL, expand=True),
        ], spacing=12),
        padding=18, bgcolor=CARD,
        border=ft.border.all(2, CORAL), border_radius=16,
        on_click=logout, ink=True,
    )

    return ListView([
        hero, stat_row,
        Divider(height=8, color=LINE),
        Text("การตั้งค่าบัญชี", size=13, weight="bold", color=SOFT),
        edit_profile_row,
        change_pw_row,
        Divider(height=8, color=LINE),
        logout_btn,
    ], spacing=12, padding=18, expand=True)

# ==================== MAIN APP BUILDER ====================
def build_app(page: Page):
    page.controls.clear()
    page.overlay.clear()

    if not current_user:
        def on_login(user):
            global current_user, _user_cache
            current_user = user; _user_cache = {}
            build_app(page)
        page.add(build_login_screen(page, on_login))
        page.update()
        return

    nav_items = [
        {"label": "หน้าหลัก", "icon": icons.HOME,           "builder": task_tab},
        {"label": "เพลง",     "icon": icons.MUSIC_NOTE,     "builder": music_screen},
        {"label": "โปรไฟล์", "icon": icons.PERSON,          "builder": profile_screen},
    ]
    selected = [0]
    page._nav_items = nav_items
    page._nav_selected = selected

    try:
        initial_content = nav_items[selected[0]]["builder"](page)
    except Exception as ex:
        print("[BUILD_APP] failed to build initial content:", ex)
        traceback.print_exc()
        initial_content = Container(
            Column(
                [
                    Text("เกิดข้อผิดพลาดในการโหลดหน้า", size=18, weight="bold", color=CORAL),
                    Text(str(ex), size=12, color=DARK),
                    Text("ลองปิดแล้วเปิดแอปใหม่อีกครั้ง", size=11, color=SOFT),
                ],
                spacing=8,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                alignment=MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment(0, 0),
            padding=20,
        )

    main_content = Container(
        content=initial_content,
        expand=True,
    )
    page._main_content = main_content

    def on_nav_change(e):
        idx = e.control.selected_index
        selected[0] = idx
        # ✅ ไม่ clear overlay ทั้งหมดตอนเปลี่ยนหน้า เพราะจะลบ Audio ออกด้วย
        # ล้างเฉพาะ Dialog (AlertDialog) ที่ค้างอยู่
        dialogs_to_remove = [c for c in page.overlay
                             if isinstance(c, AlertDialog)]
        for d in dialogs_to_remove:
            page.overlay.remove(d)

        refresh_main_content(page)

    nav_bar = NavigationBar(
        destinations=[NavigationBarDestination(icon=item["icon"], label=item["label"])
                      for item in nav_items],
        selected_index=selected[0],
        on_change=on_nav_change,
        bgcolor=CARD, indicator_color=PEACH_P,
        label_behavior="alwaysShow",
        height=68,
    )

    page.add(Column([main_content, nav_bar], expand=True, spacing=0))
    page.update()

# ฟอนต์ Prompt ในเครื่อง (โหลดเร็วกว่า Google Fonts บนเว็บ — ไทยขึ้นชัดเร็วขึ้น)
_PROMPT_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_PROMPT_TTF = _PROMPT_FONT_DIR / "Prompt-Regular.ttf"


# ==================== ENTRY POINT ====================
def main(page: ft.Page):
    page.title             = "Pomo Focus"
    page.theme_mode        = ThemeMode.LIGHT
    if _PROMPT_TTF.is_file():
        page.fonts = {"Prompt": "fonts/Prompt-Regular.ttf"}
    else:
        page.fonts = {
            "Prompt": "https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap"
        }
    page.theme             = ft.Theme(font_family="Prompt")
    page.bgcolor           = BG
    page.window_width      = 460
    page.window_height     = 860
    page.window_min_width  = 380
    page.window_min_height = 640
    build_app(page)


async def _pomodoro_flet_run_web_server(
    main,
    before_main,
    host,
    port,
    page_name,
    assets_dir,
    upload_dir,
    web_renderer,
    route_url_strategy,
    no_cdn,
    on_startup,
):
    """
    เหมือน flet.app.__run_web_server แต่ถ้า bind ที่ 0.0.0.0 จะให้ URL ในเบราว์เซอร์เป็น 127.0.0.1
    (ที่อยู่ http://0.0.0.0/ ใช้เปิดใน Edge/Chrome ไม่ได้ — ERR_ADDRESS_INVALID)
    """
    import logging

    from flet.app import ensure_flet_web_package_installed
    from flet.utils import get_free_tcp_port

    ensure_flet_web_package_installed()
    from flet_web.fastapi.serve_fastapi_web_app import serve_fastapi_web_app

    url_host = "127.0.0.1" if host in (None, "", "*", "0.0.0.0") else host

    if port == 0:
        port = get_free_tcp_port()

    flog = logging.getLogger("flet")
    flog.info("Starting Flet web server on port %s...", port)

    log_level = flog.getEffectiveLevel()
    if log_level == logging.CRITICAL or log_level == logging.NOTSET:
        log_level = logging.FATAL

    return await serve_fastapi_web_app(
        main,
        before_main=before_main,
        host=host,
        url_host=url_host,
        port=port,
        page_name=page_name,
        assets_dir=assets_dir,
        upload_dir=upload_dir,
        web_renderer=web_renderer,
        route_url_strategy=route_url_strategy,
        no_cdn=no_cdn,
        on_startup=on_startup,
        log_level=logging.getLevelName(log_level).lower(),
    )


def _apply_flet_web_browser_url_patch():
    import flet.app as flet_app

    if getattr(flet_app, "_pomodoro_browser_url_patch", False):
        return
    flet_app._pomodoro_browser_url_patch = True
    flet_app.__run_web_server = _pomodoro_flet_run_web_server


if __name__ == "__main__":
    # default: desktop app, optional: web mode for phone preview
    import argparse

    # ช่วงพอร์ตที่ลองผูกกับ default 8550: 8550..8581 — ต้องตรงกับ setup_windows_firewall.ps1
    _FLET_WEB_PORT_FIRST = 8550
    _FLET_WEB_BIND_TRIES = 32
    _FLET_WEB_PORT_LAST = _FLET_WEB_PORT_FIRST + _FLET_WEB_BIND_TRIES - 1  # 8581

    parser = argparse.ArgumentParser()
    parser.add_argument("--web", action="store_true", help="Run as web app")
    # 0.0.0.0 = รับจากมือถือใน LAN ได้; 127.0.0.1 = เปิดเฉพาะเครื่องนี้
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address for web mode (use 127.0.0.1 for local-only)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_FLET_WEB_PORT_FIRST,
        help="First port to try for web mode (then up to %s if busy)" % _FLET_WEB_PORT_LAST,
    )
    args = parser.parse_args()

    if args.web:
        _apply_flet_web_browser_url_patch()
        import socket

        def _guess_lan_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.5)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except OSError:
                return None

        def _pick_listen_port(
            bind_host: str, preferred: int, span: int = _FLET_WEB_BIND_TRIES
        ) -> int:
            """หาพอร์ตว่าง; ถ้า preferred ถูกใช้ (เช่น instance เก่าค้าง) ลองถัดไป"""
            last_exc = None
            for p in range(preferred, preferred + span):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((bind_host, p))
                    s.close()
                    if p != preferred:
                        print(
                            "NOTE: port %s is in use — using %s instead "
                            "(close old terminal or: Taskkill /PID <pid> /F)"
                            % (preferred, p)
                        )
                    return p
                except OSError as e:
                    last_exc = e
                    try:
                        s.close()
                    except OSError:
                        pass
            raise OSError(
                "No free TCP port in %s..%s — close apps using those ports. Last error: %s"
                % (preferred, preferred + span - 1, last_exc)
            )

        listen_port = _pick_listen_port(args.host, args.port)
        lan = _guess_lan_ip()
        print()
        print("=" * 62)
        print("Flet WEB: leave this window open while using the app.")
        print("  On PC:    http://127.0.0.1:%s  (do NOT use http://0.0.0.0:... in browser)" % listen_port)
        if lan:
            print("  On phone: http://%s:%s  (same Wi-Fi as this PC)" % (lan, listen_port))
        else:
            print("  On phone: http://<this_PC_LAN_ip>:%s  (see ipconfig)" % listen_port)
        print("  Also run: python pomodoro_api.py  (API base %s)" % api_base())
        print("Use http:// on the phone (not https). Port %s is in range 8550-8581" % listen_port)
        print("  (re-run setup_windows_firewall.bat so Public+Private allow this range).")
        print("iPhone Personal Hotspot: PC often gets 172.20.10.x — Windows may label it")
        print("  Public; firewall must allow that profile. If Safari still fails, try")
        print("  home Wi-Fi for both devices, or another phone/PC on the same hotspot.")
        print("If phone says server stopped: closed terminal, wrong IP, PC sleep,")
        print("  or guest Wi-Fi isolation blocking device-to-device.")
        print('If stuck on "Working...": keep this terminal running (no prompt below);')
        print("  try Edge DevTools (F12) > Console for ws errors; no_cdn=True is on.")
        print("=" * 62)
        print()

        ft.run(
            main,
            view=ft.AppView.WEB_BROWSER,
            host=args.host,
            port=listen_port,
            assets_dir="assets",
            # ลดการโหลด CanvasKit/font จาก CDN — ถ้าค้างที่ "Working..." บ่อยมักแก้ได้
            no_cdn=True,
        )
    else:
        ft.run(main, assets_dir="assets")
