from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import hashlib
import calendar
from typing import cast

DATABASE_URL = "mysql+pymysql://root:FouardSule1@localhost:3306/aurora_core"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True)
    password = Column(String(200))
    role = Column(String(20), default="agent")


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    phone = Column(String(20))
    daily_amount = Column(Float, default=0)
    total_saved = Column(Float, default=0)
    collector_id = Column(Integer, default=1)


class Collection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    collector_id = Column(Integer)
    amount = Column(Float)
    date = Column(DateTime, default=datetime.now)


# --- THIS WILL FIX YOUR 500 ERROR ---

Base.metadata.create_all(bind=engine)

# Auto create admin
db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", password=hash_password("admin123"), role="admin"))
    db.commit()
    print("✅ Admin created: admin / admin123")
db.close()


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "agent"


class LoginData(BaseModel):
    username: str
    password: str


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "AURORA Running"}


@app.post("/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username exists")
    new_user = User(
        username=user.username, password=hash_password(user.password), role=user.role
    )
    db.add(new_user)
    db.commit()
    return {"message": f"User {user.username} created"}


@app.post("/auth/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or user.password != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"access_token": "token123", "username": user.username, "role": user.role}


@app.post("/api/members/add")
def add_member(
    collector_id: int,
    full_name: str,
    phone: str,
    daily_amount: float,
    db: Session = Depends(get_db),
):
    m = Member(
        full_name=full_name,
        phone=phone,
        daily_amount=daily_amount,
        collector_id=collector_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@app.get("/api/members")
def get_members(db: Session = Depends(get_db)):
    return db.query(Member).all()


@app.post("/api/collect")
def collect(
    collector_id: int, member_id: int, amount: float, db: Session = Depends(get_db)
):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    setattr(member, "total_saved", cast(float, member.total_saved) + amount)
    db.add(Collection(member_id=member_id, collector_id=collector_id, amount=amount))
    db.commit()
    return {"message": f"Collected {amount}", "new_total": member.total_saved}


@app.post("/api/withdraw")
def withdraw(member_id: int, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # SMART: Get current month days
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]  # 28,29,30,31

    # Option 1: Always 31 (traditional) - Uncomment this:
    # days_in_month = 31

    daily_amount = cast(float, member.daily_amount)
    total_saved = cast(float, member.total_saved)
    min_required = daily_amount * days_in_month
    if total_saved < min_required:
        needed = (
            days_in_month - int(total_saved / daily_amount)
            if daily_amount > 0
            else days_in_month
        )
        raise HTTPException(
            status_code=400,
            detail=f"Month {now.month}/{now.year} has {days_in_month} days. Needs GHC {min_required}, has GHC {member.total_saved}. Collect {needed} days more",
        )

    commission = member.daily_amount
    payout = member.total_saved - commission
    setattr(member, "total_saved", 0)
    db.commit()

    return {
        "message": f"Payout GHC {payout} to {member.full_name}",
        "payout": payout,
        "commission": commission,
        "month": f"{now.month}/{now.year} ({days_in_month} days)",
        "profit": f"Your profit: GHC {commission}",
    }

    commission = member.daily_amount
    payout = member.total_saved - commission

    # Reset after payout
    # SQLAlchemy's declarative Column typing rejects direct assignment here;
    # setattr preserves the runtime ORM update while satisfying static checks.
    setattr(member, "total_saved", 0)
    db.commit()

    return {
        "message": f"Payout GHC {payout} to {member.full_name}",
        "payout": payout,
        "commission": commission,
        "commission_kept": f"Your profit: GHC {commission}",
    }


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    members = db.query(Member).all()
    total_members = len(members)
    total_saved = sum([m.total_saved for m in members])
    total_commission_estimate = sum([m.daily_amount for m in members])  # potential
    return {
        "total_members": total_members,
        "total_saved": total_saved,
        "potential_commission": total_commission_estimate,
    }
