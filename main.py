import os
import hmac
import hashlib
import json
import datetime
import jwt
from typing import Optional, List
from urllib.parse import unquote

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func, desc
from passlib.context import CryptContext

# Import core modules
from config import settings
from database import engine, Base, get_db
import models

# App initialization
app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# Enable CORS for external endpoints/widgets if required
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and templates folders
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password utility context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# LIFE CYCLE / INITIALIZATION HOOKS
# ==========================================
@app.on_event("startup")
async def startup_event():
    # Automatically seed tables asynchronously
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Core Application Settings row and Master Admin account if not present
    async with AsyncSession(engine) as session:
        try:
            # Check for settings entries
            set_stmt = select(models.Settings).limit(1)
            result = await session.execute(set_stmt)
            if not result.scalar_one_or_none():
                app_settings = models.Settings(
                    app_name=settings.APP_NAME,
                    min_withdraw=settings.DEFAULT_MIN_WITHDRAW,
                    max_withdraw=settings.DEFAULT_MAX_WITHDRAW,
                    ref_l1_reward=settings.DEFAULT_REF_L1_REWARD,
                    ref_l2_reward=settings.DEFAULT_REF_L2_REWARD,
                    ref_l3_reward=settings.DEFAULT_REF_L3_REWARD
                )
                session.add(app_settings)
            
            # Check for default Admin account entries
            adm_stmt = select(models.Admin).where(models.Admin.username == settings.DEFAULT_ADMIN_USERNAME)
            adm_res = await session.execute(adm_stmt)
            if not adm_res.scalar_one_or_none():
                hashed_pass = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
                master_admin = models.Admin(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    password_hash=hashed_pass,
                    role="SuperAdmin"
                )
                session.add(master_admin)
                
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"[STARTUP ERROR] Seeding failed: {str(e)}")


# ==========================================
# AUTHENTICATION & SECURITY UTILITIES
# ==========================================
def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    """
    Validates data received from the Telegram Mini App using the bot token.
    Implements mandatory Telegram HMAC SHA256 security signatures.
    """
    try:
        if not init_data:
            return None
        
        parsed_data = dict(qc.split("=") for qc in unquote(init_data).split("&"))
        if "hash" not in parsed_data:
            return None
        
        data_hash = parsed_data.pop("hash")
        sorted_params = sorted([f"{k}={v}" for k, v in parsed_data.items()])
        data_check_string = "\n".join(sorted_params)
        
        secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == data_hash:
            return json.loads(parsed_data.get("user", "{}"))
        return None
    except Exception:
        return None

def create_jwt_token(data: dict) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_admin(request: Request) -> Optional[str]:
    """Retrieve verified active admin via session cookied tokens."""
    token = request.cookies.get("admin_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("role") in ["SuperAdmin", "Admin"]:
            return payload.get("sub")
    except jwt.PyJWTError:
        return None
    return None


# ==========================================
# PAGES & WEB INTERFACES (JINJA2 MAPS)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def serve_app_index(request: Request):
    """Primary application entrypoint. Automatically serves responsive dark-glass UI."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin/login", response_class=HTMLResponse)
async def serve_admin_login(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "view_admin_login": True})


# ==========================================
# USER & TELEGRAM MINI APP API INTERFACES
# ==========================================
@app.post("/api/auth/telegram")
async def telegram_webapp_authentication(payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Validates authentic secure data from Telegram Mini App container,
    provisions new users automatically, logs IP/Device contexts, handles referrals up to Level 3.
    """
    init_data = payload.get("init_data")
    referrer_id = payload.get("referrer_id") # Optional tracking ref variable passed from deep-linking
    
    tg_user = verify_telegram_init_data(init_data)
    if not tg_user:
        # Fallback for localized debugging workflows only if token equals dummy schema
        if settings.TELEGRAM_BOT_TOKEN == "1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ":
            tg_user = {"id": 9999999, "username": "Test_Luxury_User", "first_name": "R8", "last_name": "Developer"}
        else:
            raise HTTPException(status_code=401, detail="Invalid Telegram signature data validation failure.")
            
    tg_id = tg_user.get("id")
    
    # Locate user or initiate auto-provisioning system
    user_stmt = select(models.User).where(models.User.telegram_id == tg_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    
    is_new = False
    if not user:
        is_new = True
        user = models.User(
            telegram_id=tg_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            language_code=tg_user.get("language_code", "en"),
            ip_address=request.client.host,
            device_info=request.headers.get("user-agent", "Unknown Environment")
        )
        db.add(user)
        await db.flush() # Yields user.id
        
        # Instantiate accompanying wallet accounts
        wallet = models.Wallet(user_id=user.id)
        db.add(wallet)
        
        # Process Multi-Level Tier Referral structures if provided safely
        if referrer_id and str(referrer_id).isdigit() and int(referrer_id) != tg_id:
            ref_stmt = select(models.User).where(models.User.telegram_id == int(referrer_id))
            ref_res = await db.execute(ref_stmt)
            referrer = ref_res.scalar_one_or_none()
            
            if referrer:
                # Find tier history properties of the level 1 referrer to populate levels 2 & 3
                parent_ref_stmt = select(models.Referral).where(models.Referral.referred_id == referrer.id)
                parent_ref_res = await db.execute(parent_ref_stmt)
                parent_ref = parent_ref_res.scalar_one_or_none()
                
                l2 = parent_ref.level_1_id if parent_ref else None
                l3 = parent_ref.level_2_id if parent_ref else None
                
                new_ref_node = models.Referral(
                    referrer_id=referrer.id,
                    referred_id=user.id,
                    level_1_id=referrer.id,
                    level_2_id=l2,
                    level_3_id=l3
                )
                db.add(new_ref_node)
                
                # Fetch System Payout Constants
                sett_stmt = select(models.Settings).limit(1)
                sett_res = await db.execute(sett_stmt)
                cfg = sett_res.scalar_one()
                
                # Distribute Level 1 Reward immediately
                ref_wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == referrer.id)
                ref_wallet_res = await db.execute(ref_wallet_stmt)
                ref_wallet = ref_wallet_res.scalar_one()
                ref_wallet.balance += cfg.ref_l1_reward
                ref_wallet.lifetime_earnings += cfg.ref_l1_reward
                
                db.add(models.Transaction(
                    user_id=referrer.id, amount=cfg.ref_l1_reward, type="referral",
                    description=f"Referral reward L1: User @{user.username or user.id}"
                ))
                
                # Distribute Level 2 Reward
                if l2:
                    l2_wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == l2)
                    l2_wallet_res = await db.execute(l2_wallet_stmt)
                    l2_w = l2_wallet_res.scalar_one_or_none()
                    if l2_w:
                        l2_w.balance += cfg.ref_l2_reward
                        l2_w.lifetime_earnings += cfg.ref_l2_reward
                        db.add(models.Transaction(
                            user_id=l2, amount=cfg.ref_l2_reward, type="referral",
                            description=f"Referral reward L2: Indirect downstream user registration"
                        ))
                
                # Distribute Level 3 Reward
                if l3:
                    l3_wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == l3)
                    l3_wallet_res = await db.execute(l3_wallet_stmt)
                    l3_w = l3_wallet_res.scalar_one_or_none()
                    if l3_w:
                        l3_w.balance += cfg.ref_l3_reward
                        l3_w.lifetime_earnings += cfg.ref_l3_reward
                        db.add(models.Transaction(
                            user_id=l3, amount=cfg.ref_l3_reward, type="referral",
                            description=f"Referral reward L3: Indirect downstream user registration"
                        ))

        await db.commit()
    else:
        if user.is_banned:
            raise HTTPException(status_code=403, detail="Your premium access has been permanently restricted due to fraud detection rules.")
            
    # Session access tokens mapping
    token = create_jwt_token({"sub": str(user.telegram_id), "role": "User"})
    return {"token": token, "is_new": is_new}

def get_current_user_dependency(request: Request) -> str:
    """Security verification extract mapping for explicit headers parsing parameters."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized API Token reference sequence context.")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token validation cycle signature timed out.")

@app.get("/api/user/profile")
async def get_user_dashboard_payload(tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    # Pull profile dataset across unified dependencies
    stmt = select(models.User).where(models.User.telegram_id == int(tg_id))
    res = await db.execute(stmt)
    user = res.scalar_one()
    
    wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == user.id)
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one()
    
    # Compute active downstream structural network trees
    ref_count_stmt = select(func.count(models.Referral.id)).where(models.Referral.referrer_id == user.id)
    ref_count_res = await db.execute(ref_count_stmt)
    ref_count = ref_count_res.scalar_one()
    
    # Load dynamic app wide context metrics configuration parameters
    sett_stmt = select(models.Settings).limit(1)
    sett_res = await db.execute(sett_stmt)
    cfg = sett_res.scalar_one()
    
    return {
        "user_info": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username or f"R8_User_{user.id}",
            "first_name": user.first_name,
            "vip_level": user.vip_level,
            "xp": user.xp,
            "referral_link": f"https://t.me/R8Earn_Bot/app?startapp={user.telegram_id}"
        },
        "wallet": {
            "balance": wallet.balance,
            "pending_balance": wallet.pending_balance,
            "lifetime_earnings": wallet.lifetime_earnings,
            "bonus_balance": wallet.bonus_balance,
            "locked_balance": wallet.locked_balance,
            "today_earnings": wallet.today_earnings
        },
        "referral_count": ref_count,
        "app_notice": cfg.notice,
        "maintenance": cfg.maintenance_mode
    }


# ==========================================
# CORE EARNING SYSTEMS & INTERFACES (TASKS/ADS)
# ==========================================
@app.get("/api/tasks/list")
async def get_available_tasks_list(tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    user_stmt = select(models.User).where(models.User.telegram_id == int(tg_id))
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one()
    
    # Map tasks that user hasn't finished, or those with positive cooling down properties
    comp_stmt = select(models.CompletedTask.task_id).where(models.CompletedTask.user_id == user.id)
    comp_res = await db.execute(comp_stmt)
    completed_ids = comp_res.scalars().all()
    
    task_stmt = select(models.Task).where(models.Task.status == True).order_by(models.Task.priority.desc())
    task_res = await db.execute(task_stmt)
    all_tasks = task_res.scalars().all()
    
    output = []
    for t in all_tasks:
        if t.id not in completed_ids or t.cooldown > 0:
            output.append({
                "id": t.id, "title": t.title, "description": t.description, "image": t.image,
                "reward": t.reward, "category": t.category, "difficulty": t.difficulty,
                "task_url": t.task_url, "verification_type": t.verification_type
            })
    return output

@app.post("/api/tasks/action")
async def execute_task_action(payload: dict, tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    task_id = payload.get("task_id")
    action_type = payload.get("action") # "start", "verify"
    proof = payload.get("proof", "Completed Automated Step Engine Verification Flow")
    
    user_stmt = select(models.User).where(models.User.telegram_id == int(tg_id))
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one()
    
    task_stmt = select(models.Task).where(models.Task.id == task_id)
    task_res = await db.execute(task_stmt)
    task = task_res.scalar_one_or_none()
    
    if not task or not task.status:
        raise HTTPException(status_code=404, detail="Requested engine target task context invalid or closed.")
        
    if action_type == "start":
        return {"status": "Started", "msg": "Task initiated successfully. Complete requirements then claim."}
        
    elif action_type == "verify":
        # Check duplicate history
        dup_stmt = select(models.CompletedTask).where(
            models.CompletedTask.user_id == user.id,
            models.CompletedTask.task_id == task.id
        )
        dup_res = await db.execute(dup_stmt)
        existing = dup_res.scalar_one_or_none()
        
        if existing and task.cooldown == 0:
            raise HTTPException(status_code=400, detail="Task already processed by tracking instance entity.")
            
        wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == user.id)
        wallet_res = await db.execute(wallet_stmt)
        wallet = wallet_res.scalar_one()
        
        if task.verification_type == "Auto":
            # Auto-approval distributes balance immediately
            new_comp = models.CompletedTask(user_id=user.id, task_id=task.id, status="Approved", proof_submitted=proof)
            db.add(new_comp)
            
            wallet.balance += task.reward
            wallet.lifetime_earnings += task.reward
            wallet.today_earnings += task.reward
            user.xp += 15 # Add static experience progression unit
            
            db.add(models.Transaction(
                user_id=user.id, amount=task.reward, type="task",
                description=f"Completed task: {task.title}", reference_id=str(task.id)
            ))
            await db.commit()
            return {"status": "Approved", "balance": wallet.balance}
        else:
            # Manual processing moves target allocations into intermediate pending state pipelines
            new_comp = models.CompletedTask(user_id=user.id, task_id=task.id, status="Pending", proof_submitted=proof)
            db.add(new_comp)
            
            wallet.pending_balance += task.reward
            await db.commit()
            return {"status": "Pending", "msg": "Proof queued safely for system compliance verification."}

@app.post("/api/earn/daily")
async def claim_daily_streak_allowance(tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(models.User).where(models.User.telegram_id == int(tg_id)))).scalar_one()
    wallet = (await db.execute(select(models.Wallet).where(models.Wallet.user_id == user.id))).scalar_one()
    cfg = (await db.execute(select(models.Settings).limit(1))).scalar_one()
    
    now = datetime.datetime.utcnow()
    if wallet.last_daily_claim and (now - wallet.last_daily_claim).total_seconds() < 86400:
        raise HTTPException(status_code=400, detail="Daily bonus timeline cooldown window active.")
        
    wallet.balance += cfg.daily_reward
    wallet.lifetime_earnings += cfg.daily_reward
    wallet.today_earnings += cfg.daily_reward
    wallet.last_daily_claim = now
    
    db.add(models.Transaction(user_id=user.id, amount=cfg.daily_reward, type="daily_reward", description="Claimed system calendar login allowance bonus."))
    await db.commit()
    return {"balance": wallet.balance, "claimed": cfg.daily_reward}

@app.get("/api/earn/ads")
async def fetch_available_advertisements(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(models.Ads).where(models.Ads.status == True))).scalars().all()

@app.post("/api/earn/ads/watch")
async def trigger_ads_payout_allocation(payload: dict, tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    ad_id = payload.get("ad_id")
    user = (await db.execute(select(models.User).where(models.User.telegram_id == int(tg_id)))).scalar_one()
    wallet = (await db.execute(select(models.Wallet).where(models.Wallet.user_id == user.id))).scalar_one()
    ad = (await db.execute(select(models.Ads).where(models.Ads.id == ad_id))).scalar_one()
    
    # Append tracking statistics metrics definitions
    ad.total_views += 1
    ad.total_payout += ad.reward
    
    wallet.balance += ad.reward
    wallet.lifetime_earnings += ad.reward
    wallet.today_earnings += ad.reward
    
    db.add(models.Transaction(user_id=user.id, amount=ad.reward, type="bonus", description=f"Watched premium sponsor ad segment: {ad.title}"))
    await db.commit()
    return {"balance": wallet.balance, "reward": ad.reward}


# ==========================================
# GAMIFICATION & SYSTEMS (SPIN / BOX / LEADERBOARD)
# ==========================================
@app.post("/api/games/spin")
async def trigger_lucky_wheel_spin(tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    import random
    user = (await db.execute(select(models.User).where(models.User.telegram_id == int(tg_id)))).scalar_one()
    wallet = (await db.execute(select(models.Wallet).where(models.Wallet.user_id == user.id))).scalar_one()
    
    now = datetime.datetime.utcnow()
    if wallet.last_spin_time and (now - wallet.last_spin_time).total_seconds() < 3600:
        raise HTTPException(status_code=400, detail="Wheel engine requires 1 hour cycle interval cooling windows.")
        
    prizes = [5.0, 10.0, 25.0, 50.0, 0.0, 100.0, 2.0, 15.0]
    win = random.choice(prizes)
    
    wallet.balance += win
    wallet.lifetime_earnings += win
    wallet.last_spin_time = now
    
    db.add(models.Transaction(user_id=user.id, amount=win, type="spin", description=f"Resulted wheel mechanical drop allocation reward: {win} coins."))
    await db.commit()
    return {"win": win, "balance": wallet.balance}

@app.get("/api/leaderboard")
async def get_global_rankings_metrics(db: AsyncSession = Depends(get_db)):
    stmt = select(models.User.username, models.User.vip_level, models.Wallet.lifetime_earnings).\
        join(models.Wallet, models.User.id == models.Wallet.user_id).\
        order_by(models.Wallet.lifetime_earnings.desc()).limit(25)
    res = await db.execute(stmt)
    records = res.all()
    return [{"username": r[0] or "Anonymous", "vip_level": r[1], "earnings": r[2]} for r in records]


# ==========================================
# TRANSACTION & WITHDRAWAL GATEWAYS
# ==========================================
@app.post("/api/withdraw/request")
async def log_financial_withdraw_pipeline(payload: dict, tg_id: str = Depends(get_current_user_dependency), db: AsyncSession = Depends(get_db)):
    method = payload.get("method") # bKash, Nagad, Rocket
    account = payload.get("account")
    amount = float(payload.get("amount", 0))
    
    if method not in ["bKash", "Nagad", "Rocket"]:
        raise HTTPException(status_code=400, detail="Unsupported payment gateway module context.")
        
    user = (await db.execute(select(models.User).where(models.User.telegram_id == int(tg_id)))).scalar_one()
    wallet = (await db.execute(select(models.Wallet).where(models.Wallet.user_id == user.id))).scalar_one()
    cfg = (await db.execute(select(models.Settings).limit(1))).scalar_one()
    
    if amount < cfg.min_withdraw or amount > cfg.max_withdraw:
        raise HTTPException(status_code=400, detail=f"Amount falls outside permitted system limits ({cfg.min_withdraw} - {cfg.max_withdraw}).")
        
    if wallet.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient fluid balance inside available user instance.")
        
    fee = amount * (cfg.withdraw_fee_percent / 100.0)
    payable = amount - fee
    
    # Deduct structural asset fields before queuing requests
    wallet.balance -= amount
    
    new_w = models.Withdraw(
        user_id=user.id, method=method, account_number=account,
        amount=amount, fee=fee, payable_amount=payable, status="Pending"
    )
    db.add(new_w)
    
    db.add(models.Transaction(user_id=user.id, amount=-amount, type="withdraw", description=f"Requested withdrawal to {method} account {account}"))
    await db.commit()
    return {"status": "Pending", "msg": "Financial withdrawal request submitted safely to auditing pipelines.", "remaining": wallet.balance}


# ==========================================
# BACKOFFICE ADMIN PANEL ENDPOINTS
# ==========================================
@app.post("/api/admin/token")
async def administrative_token_generation(username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    stmt = select(models.Admin).where(models.Admin.username == username)
    res = await db.execute(stmt)
    admin = res.scalar_one_or_none()
    
    if not admin or not pwd_context.verify(password, admin.password_hash):
        return JSONResponse(status_code=401, content={"msg": "Invalid credentials."})
        
    token = create_jwt_token({"sub": admin.username, "role": "Admin"})
    response = JSONResponse(content={"status": "Success", "redirect": "/?view=admin_dashboard"})
    response.set_cookie(key="admin_token", value=token, httponly=True, max_age=86400)
    return response

@app.get("/api/admin/analytics")
async def pull_system_analytics(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    
    users_cnt = (await db.execute(select(func.count(models.User.id)))).scalar_one()
    total_withdrawn = (await db.execute(select(func.sum(models.Withdraw.amount)).where(models.Withdraw.status == "Paid"))).scalar_one() or 0.0
    pending_w_cnt = (await db.execute(select(func.count(models.Withdraw.id)).where(models.Withdraw.status == "Pending"))).scalar_one()
    pending_tasks_cnt = (await db.execute(select(func.count(models.CompletedTask.id)).where(models.CompletedTask.status == "Pending"))).scalar_one()
    
    return {
        "metrics": {
            "total_users": users_cnt, "total_paid_withdraws": total_withdrawn,
            "pending_withdrawals": pending_w_cnt, "pending_manual_tasks": pending_tasks_cnt
        }
    }

@app.get("/api/admin/users")
async def admin_list_users(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    stmt = select(models.User.id, models.User.telegram_id, models.User.username, models.User.vip_level, models.User.is_banned, models.Wallet.balance).\
        join(models.Wallet, models.User.id == models.Wallet.user_id)
    res = await db.execute(stmt)
    return [{"id": r[0], "telegram_id": r[1], "username": r[2], "vip": r[3], "banned": r[4], "balance": r[5]} for r in res.all()]

@app.post("/api/admin/users/action")
async def admin_user_action_execution(payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    target_id = payload.get("user_id")
    action = payload.get("action") # "ban", "unban", "reward"
    val = payload.get("value", 0)
    
    if action == "ban":
        await db.execute(update(models.User).where(models.User.id == target_id).values(is_banned=True))
    elif action == "unban":
        await db.execute(update(models.User).where(models.User.id == target_id).values(is_banned=False))
    elif action == "reward":
        wallet = (await db.execute(select(models.Wallet).where(models.Wallet.user_id == target_id))).scalar_one()
        wallet.balance += float(val)
        db.add(models.Transaction(user_id=target_id, amount=float(val), type="bonus", description="Manually adjusted administrative credit drop."))
        
    await db.commit()
    return {"status": "Success"}

@app.get("/api/admin/withdrawals")
async def admin_list_withdrawals(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    stmt = select(models.Withdraw.id, models.User.username, models.Withdraw.method, models.Withdraw.account_number, models.Withdraw.amount, models.Withdraw.status).\
        join(models.User, models.Withdraw.user_id == models.User.id).order_by(models.Withdraw.created_at.desc())
    res = await db.execute(stmt)
    return [{"id": r[0], "username": r[1], "method": r[2], "account": r[3], "amount": r[4], "status": r[5]} for r in res.all()]

@app.post("/api/admin/withdrawals/process")
async def process_withdrawal_request(payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    w_id = payload.get("withdraw_id")
    action = payload.get("action") # "Approve", "Reject"
    tx_num = payload.get("tx_number", "TXN-MANUAL-PROCESSED")
    note = payload.get("admin_note", "Approved via corporate ecosystem dashboard panel asset layer.")
    
    w_stmt = select(models.Withdraw).where(models.Withdraw.id == w_id)
    w_res = await db.execute(w_stmt)
    withdrawal = w_res.scalar_one()
    
    if withdrawal.status != "Pending":
        raise HTTPException(status_code=400, detail="Transaction has already departed pending execution loops.")
        
    if action == "Approve":
        withdrawal.status = "Paid"
        withdrawal.tx_number = tx_num
        withdrawal.admin_note = note
    else:
        withdrawal.status = "Rejected"
        withdrawal.admin_note = note
        # Return balances safely back to client instances
        wallet_stmt = select(models.Wallet).where(models.Wallet.user_id == withdrawal.user_id)
        wallet_res = await db.execute(wallet_stmt)
        w = wallet_res.scalar_one()
        w.balance += withdrawal.amount
        
    await db.commit()
    return {"status": "Success"}

@app.post("/api/admin/tasks/create")
async def create_new_system_task(
    title: str = Form(...), description: str = Form(...), reward: float = Form(...),
    category: str = Form(...), difficulty: str = Form(...), task_url: str = Form(...),
    verification_type: str = Form(...), request: Request = None, db: AsyncSession = Depends(get_db)
):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    new_task = models.Task(
        title=title, description=description, reward=reward, category=category,
        difficulty=difficulty, task_url=task_url, verification_type=verification_type, status=True
    )
    db.add(new_task)
    await db.commit()
    return RedirectResponse(url="/?view=admin_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/api/admin/settings/update")
async def update_global_system_settings(
    notice: str = Form(...), min_w: float = Form(...), max_w: float = Form(...),
    fee: float = Form(...), request: Request = None, db: AsyncSession = Depends(get_db)
):
    if not get_current_admin(request): raise HTTPException(status_code=403, detail="Forbidden")
    stmt = select(models.Settings).limit(1)
    res = await db.execute(stmt)
    cfg = res.scalar_one()
    
    cfg.notice = notice
    cfg.min_withdraw = min_w
    cfg.max_withdraw = max_w
    cfg.withdraw_fee_percent = fee
    
    await db.commit()
    return RedirectResponse(url="/?view=admin_dashboard", status_code=status.HTTP_303_SEE_OTHER)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
