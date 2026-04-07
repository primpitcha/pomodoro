import urllib.parse
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    create_engine,
    ForeignKey,
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Boolean,
    Text,
    or_,
    and_,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

# ==================== Configuration ====================
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "123"
DB_NAME = "Pomodoro"
DB_PORT = 3306

safe_password = urllib.parse.quote_plus("123")
DATABASE_URL = f"mysql+pymysql://root:{safe_password}@localhost:3306/Pomodoro"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# ==================== Database Models ====================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class UserSetting(Base):
    __tablename__ = "user_setting"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    work_minutes = Column(Integer)
    short_break_minutes = Column(Integer)
    long_break_minutes = Column(Integer)
    rounds_before_long_break = Column(Integer)
    selected_music_track = Column(String(100), nullable=True)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    note = Column(Text, nullable=True)
    status = Column(String(50))
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_type = Column(String(50))
    duration_minutes = Column(Integer)
    started_at = Column(DateTime)
    ended_at = Column(DateTime, nullable=True)
    completed = Column(Boolean)

# ==================== Pydantic Schemas ====================
class UserSettingSchema(BaseModel):
    work_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    rounds_before_long_break: int
    selected_music_track: Optional[str]

class UserProfileSchema(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    settings: Optional[UserSettingSchema]

class TaskSchema(BaseModel):
    id: int
    title: str
    note: Optional[str]
    status: str
    date: date
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class TaskCreateSchema(BaseModel):
    user_id: int
    title: str
    note: Optional[str]
    status: str
    date: date

class TaskUpdateSchema(BaseModel):
    title: Optional[str]
    note: Optional[str]
    status: Optional[str]

class SessionCreateSchema(BaseModel):
    task_id: Optional[int]
    user_id: int
    session_type: str
    duration_minutes: int
    started_at: datetime
    ended_at: Optional[datetime]
    completed: bool

class UserSettingUpdateSchema(BaseModel):
    work_minutes: Optional[int]
    short_break_minutes: Optional[int]
    long_break_minutes: Optional[int]
    rounds_before_long_break: Optional[int]
    selected_music_track: Optional[str]

# ── NEW ──────────────────────────────────────────────────────
class UserProfileUpdateSchema(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

class PasswordChangeSchema(BaseModel):
    old_password: str
    new_password: str
# ─────────────────────────────────────────────────────────────

# ==================== FastAPI App ====================
app = FastAPI(title="Pomodoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== Endpoints ====================

@app.get("/users/{user_id}", response_model=UserProfileSchema)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    return UserProfileSchema(
        id=user.id, username=user.username, email=user.email,
        created_at=user.created_at,
        settings=UserSettingSchema(
            work_minutes=settings.work_minutes if settings else 25,
            short_break_minutes=settings.short_break_minutes if settings else 5,
            long_break_minutes=settings.long_break_minutes if settings else 15,
            rounds_before_long_break=settings.rounds_before_long_break if settings else 4,
            selected_music_track=settings.selected_music_track if settings else None,
        ) if settings else None,
    )

@app.put("/users/{user_id}/settings")
def update_user_settings(user_id: int, data: UserSettingUpdateSchema, db: Session = Depends(get_db)):
    settings = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if not settings:
        settings = UserSetting(
            user_id=user_id,
            work_minutes=data.work_minutes or 25,
            short_break_minutes=data.short_break_minutes or 5,
            long_break_minutes=data.long_break_minutes or 15,
            rounds_before_long_break=data.rounds_before_long_break or 4,
            selected_music_track=data.selected_music_track,
        )
        db.add(settings)
    else:
        if data.work_minutes is not None:           settings.work_minutes = data.work_minutes
        if data.short_break_minutes is not None:    settings.short_break_minutes = data.short_break_minutes
        if data.long_break_minutes is not None:     settings.long_break_minutes = data.long_break_minutes
        if data.rounds_before_long_break is not None: settings.rounds_before_long_break = data.rounds_before_long_break
        if data.selected_music_track is not None:   settings.selected_music_track = data.selected_music_track
    db.commit()
    return {"message": "Settings updated successfully"}

# ── NEW: แก้ไขโปรไฟล์ ────────────────────────────────────────
@app.put("/users/{user_id}/profile")
def update_user_profile(user_id: int, data: UserProfileUpdateSchema = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.username is not None and data.username.strip():
        user.username = data.username.strip()
    if data.email is not None and data.email.strip():
        existing = db.query(User).filter(
            User.email == data.email.strip(), User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email.strip()
    db.commit()
    db.refresh(user)
    return {"status": "success", "user": {"id": user.id, "username": user.username, "email": user.email}}

# ── NEW: เปลี่ยนรหัสผ่าน ─────────────────────────────────────
@app.put("/users/{user_id}/password")
def change_password(user_id: int, data: PasswordChangeSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password_hash != data.old_password.strip():
        raise HTTPException(status_code=401, detail="รหัสผ่านเดิมไม่ถูกต้อง")
    if not data.new_password.strip():
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องไม่ว่าง")
    user.password_hash = data.new_password.strip()
    db.commit()
    return {"status": "success", "message": "เปลี่ยนรหัสผ่านสำเร็จ"}
# ─────────────────────────────────────────────────────────────

@app.get("/tasks/all/{user_id}", response_model=List[TaskSchema])
def get_all_tasks(user_id: int, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.user_id == user_id).order_by(Task.date.desc()).all()
    return tasks

@app.get("/tasks/{user_id}/{date_str}", response_model=List[TaskSchema])
def get_tasks_by_date(user_id: int, date_str: str, db: Session = Depends(get_db)):
    try:
        task_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    tasks = db.query(Task).filter(Task.user_id == user_id, Task.date == task_date).all()
    return tasks

@app.post("/tasks", response_model=TaskSchema)
def create_task(task_data: TaskCreateSchema, db: Session = Depends(get_db)):
    try:
        new_task = Task(
            user_id=task_data.user_id, title=task_data.title,
            note=task_data.note, status=task_data.status,
            date=task_data.date, created_at=datetime.utcnow(),
        )
        db.add(new_task); db.commit(); db.refresh(new_task)
        return new_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/tasks/{task_id}", response_model=TaskSchema)
def update_task(task_id: int, data: TaskUpdateSchema, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if data.title is not None:  task.title = data.title
    if data.note is not None:   task.note  = data.note
    if data.status is not None:
        task.status = data.status
        task.completed_at = datetime.utcnow() if data.status == "done" else None
    db.commit(); db.refresh(task)
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task); db.commit()
    return {"message": "Task deleted successfully"}

@app.post("/sessions")
def create_session(session_data: SessionCreateSchema, db: Session = Depends(get_db)):
    new_session = PomodoroSession(
        task_id=session_data.task_id, user_id=session_data.user_id,
        session_type=session_data.session_type,
        duration_minutes=session_data.duration_minutes,
        started_at=session_data.started_at, ended_at=session_data.ended_at,
        completed=session_data.completed,
    )
    db.add(new_session); db.commit()
    return {"message": "Session recorded successfully", "session_id": new_session.id}

@app.get("/sessions/{user_id}/stats")
def get_session_stats(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import func
    total_sessions = db.query(PomodoroSession).filter(
        PomodoroSession.user_id == user_id,
        PomodoroSession.session_type == "work",
        PomodoroSession.completed == True,
    ).count()
    total_tasks_done = db.query(Task).filter(
        Task.user_id == user_id, Task.status == "done").count()
    total_minutes = db.query(func.sum(PomodoroSession.duration_minutes)).filter(
        PomodoroSession.user_id == user_id,
        PomodoroSession.session_type == "work",
        PomodoroSession.completed == True,
    ).scalar() or 0
    today = date.today()
    today_sessions = db.query(PomodoroSession).filter(
        PomodoroSession.user_id == user_id,
        PomodoroSession.session_type == "work",
        PomodoroSession.completed == True,
        func.date(PomodoroSession.started_at) == today,
    ).count()
    today_minutes = db.query(func.sum(PomodoroSession.duration_minutes)).filter(
        PomodoroSession.user_id == user_id,
        PomodoroSession.session_type == "work",
        PomodoroSession.completed == True,
        func.date(PomodoroSession.started_at) == today,
    ).scalar() or 0
    # งานเสร็จวันนี้: เลิกใช้แค่ Task.date — ใช้วันที่ตั้ง status=done (completed_at) เป็นหลัก
    # แถวเก่าที่ completed_at ว่าง: นับเฉพาะเมื่อ Task.date ตรงวันนี้
    today_tasks_done = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == "done",
            or_(
                and_(
                    Task.completed_at.isnot(None),
                    func.date(Task.completed_at) == today,
                ),
                and_(Task.completed_at.is_(None), Task.date == today),
            ),
        )
        .count()
    )
    return {
        "total_sessions": total_sessions, "total_tasks_done": total_tasks_done,
        "total_focus_hours": round(total_minutes / 60, 1),
        "today_sessions": today_sessions, "today_tasks_done": today_tasks_done,
        "today_focus_hours": round(today_minutes / 60, 1),
    }

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("Database connected and tables are ready!")

# ==================== Login & Register ====================
class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: str
    password: str

@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email    = data.email.strip()
    password = data.password.strip()
    username = data.username.strip() if data.username else None
    user = db.query(User).filter(User.email == email, User.password_hash == password).first()
    if user:
        return {"status": "success",
                "user": {"id": user.id, "username": user.username, "email": user.email}}
    if username:
        new_user = User(username=username, email=email, password_hash=password)
        db.add(new_user); db.commit(); db.refresh(new_user)
        return {"status": "success",
                "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}}
    raise HTTPException(status_code=401, detail="Email or Password incorrect")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(username=data.username.strip(), email=email,
                    password_hash=data.password.strip())
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"status": "success",
            "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}}


if __name__ == "__main__":
    import socket
    import uvicorn

    # ลอง 8000..8031 — ต้องตรงช่วงกับ setup_windows_firewall.ps1 (FastAPI)
    _API_HOST = "0.0.0.0"
    _API_PORT_FIRST = 8000
    _API_BIND_TRIES = 32

    def _pick_api_port(bind_host: str, preferred: int, span: int) -> int:
        last_exc = None
        for p in range(preferred, preferred + span):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((bind_host, p))
                s.close()
                if p != preferred:
                    print(
                        "NOTE: API port %s in use — using %s "
                        "(app.py reads .pomodoro_api_port)"
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
            "No free API port in %s..%s: %s"
            % (preferred, preferred + span - 1, last_exc)
        )

    listen_port = _pick_api_port(_API_HOST, _API_PORT_FIRST, _API_BIND_TRIES)
    port_file = Path(__file__).resolve().parent / ".pomodoro_api_port"
    try:
        port_file.write_text(str(listen_port), encoding="utf-8")
    except OSError as exc:
        print("WARNING: could not write %s: %s" % (port_file, exc))

    print(
        "Pomodoro API on http://0.0.0.0:%s — keep this running for the Flet app."
        % listen_port
    )
    uvicorn.run(app, host=_API_HOST, port=listen_port)