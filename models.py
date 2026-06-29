import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Text, Table, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language_code = Column(String, nullable=True)
    
    # VIP & XP System
    xp = Column(Integer, default=0, nullable=False)
    vip_level = Column(Integer, default=1, nullable=False)
    
    # Status Flags
    is_admin = Column(Boolean, default=False, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    is_muted = Column(Boolean, default=False, nullable=False)
    
    # Tracking logs
    ip_address = Column(String, nullable=True)
    device_info = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    wallet = relationship("Wallet", uselist=False, back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    withdraws = relationship("Withdraw", back_populates="user", cascade="all, delete-orphan")
    completed_tasks = relationship("CompletedTask", back_populates="user", cascade="all, delete-orphan")
    referrals_initiated = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referral_received = relationship("Referral", foreign_keys="Referral.referred_id", uselist=False, back_populates="referred")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    balance = Column(Float, default=0.0, nullable=False)          # Main withdrawable balance (Coins)
    pending_balance = Column(Float, default=0.0, nullable=False)  # Under review from manual tasks
    lifetime_earnings = Column(Float, default=0.0, nullable=False)
    bonus_balance = Column(Float, default=0.0, nullable=False)
    locked_balance = Column(Float, default=0.0, nullable=False)
    
    # Daily Tracking
    today_earnings = Column(Float, default=0.0, nullable=False)
    last_daily_claim = Column(DateTime, nullable=True)
    last_spin_time = Column(DateTime, nullable=True)
    last_box_time = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # "task", "referral", "daily_reward", "spin", "lucky_box", "withdraw", "penalty", "bonus"
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True) # ID mapping to specific task/withdraw/ref entity
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="transactions")


class Withdraw(Base):
    __tablename__ = "withdraws"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    method = Column(String, nullable=False) # "bKash", "Nagad", "Rocket"
    account_number = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0, nullable=False)
    payable_amount = Column(Float, nullable=False)
    status = Column(String, default="Pending", nullable=False) # "Pending", "Approved", "Rejected", "Paid", "Cancelled"
    tx_number = Column(String, nullable=True) # Operational payment confirmation TX hash/ID
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="withdraws")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String, default="default_task.png", nullable=False)
    reward = Column(Float, nullable=False)
    category = Column(String, nullable=False) # "Telegram", "Facebook", "YouTube", "Twitter", "Custom", "Ads", etc.
    difficulty = Column(String, default="Easy", nullable=False) # "Easy", "Medium", "Hard"
    cooldown = Column(Integer, default=0, nullable=False) # In seconds (0 = claim once)
    expiry = Column(DateTime, nullable=True)
    verification_type = Column(String, default="Auto", nullable=False) # "Auto", "Manual"
    task_url = Column(String, nullable=False)
    status = Column(Boolean, default=True, nullable=False) # Active / Inactive
    priority = Column(Integer, default=0, nullable=False)
    max_users = Column(Integer, default=-1, nullable=False) # -1 = Unlimited
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    completed_by = relationship("CompletedTask", back_populates="task", cascade="all, delete-orphan")


class CompletedTask(Base):
    __tablename__ = "completed_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="Pending", nullable=False) # "Pending", "Approved", "Rejected"
    proof_submitted = Column(String, nullable=True) # Text submission / link or verification marker
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="completed_tasks")
    task = relationship("Task", back_populates="completed_by")


class Ads(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    ad_type = Column(String, nullable=False) # "Rewarded", "Interstitial", "Banner", "Popup", "Custom"
    reward = Column(Float, default=0.0, nullable=False)
    cooldown = Column(Integer, default=60, nullable=False) # Seconds between viewing
    daily_limit = Column(Integer, default=10, nullable=False)
    ad_code_or_url = Column(Text, nullable=False)
    status = Column(Boolean, default=True, nullable=False)
    
    # Simple Stats
    total_views = Column(Integer, default=0, nullable=False)
    total_payout = Column(Float, default=0.0, nullable=False)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    app_name = Column(String, default="R8 Earn", nullable=False)
    logo = Column(String, default="/static/logo.png", nullable=False)
    banner = Column(String, default="/static/banner.png", nullable=False)
    notice = Column(String, default="Welcome to R8 Earn Luxury Ecosystem!", nullable=False)
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    theme = Column(String, default="Dark", nullable=False)
    
    # Financial/Reward Limits
    min_withdraw = Column(Float, default=500.0, nullable=False)
    max_withdraw = Column(Float, default=10000.0, nullable=False)
    withdraw_fee_percent = Column(Float, default=0.0, nullable=False)
    daily_limit_withdrawals = Column(Integer, default=2, nullable=False)
    
    # Referral Structure
    ref_l1_reward = Column(Float, default=10.0, nullable=False)
    ref_l2_reward = Column(Float, default=5.0, nullable=False)
    ref_l3_reward = Column(Float, default=2.0, nullable=False)
    
    # Support & Communities
    support_link = Column(String, default="https://t.me/r8_support", nullable=False)
    telegram_group = Column(String, default="https://t.me/r8_group", nullable=False)
    telegram_channel = Column(String, default="https://t.me/r8_channel", nullable=False)
    facebook = Column(String, default="https://facebook.com", nullable=False)
    youtube = Column(String, default="https://youtube.com", nullable=False)
    contact_email = Column(String, default="support@r8earn.com", nullable=False)
    privacy_policy = Column(Text, default="Privacy Policy details...", nullable=False)
    terms_of_service = Column(Text, default="Terms of Service details...", nullable=False)
    version = Column(String, default="1.0.0", nullable=False)


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referred_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    level_1_id = Column(Integer, nullable=False) # Explicit tracker cache for fast tree lookups
    level_2_id = Column(Integer, nullable=True)
    level_3_id = Column(Integer, nullable=True)
    reward_distributed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_initiated")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referral_received")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) # Null means global announcement
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_popup = Column(Boolean, default=False, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False) # e.g. "LOGIN", "ANTI_CHEAT_TRIGGER", "FAILED_WITHDRAW"
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="logs")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="SuperAdmin", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
