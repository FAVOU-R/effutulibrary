from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.config import settings
from jose import jwt
import hashlib, re, os, random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_password_hash(p: str) -> str:
    salt = "effutu_ghana_salt_2026"
    return hashlib.sha256(f"{p}{salt}".encode('utf-8')).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return get_password_hash(plain) == hashed

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token") or request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def send_email(to_email: str, subject: str, body_html: str) -> bool:
    try:
        smtp_server = settings.MAIL_SERVER or settings.BREVO_SMTP_SERVER
        smtp_user = settings.MAIL_USERNAME or settings.BREVO_SMTP_USER
        smtp_pass = settings.MAIL_PASSWORD or settings.BREVO_SMTP_PASSWORD
        smtp_port = settings.MAIL_PORT or settings.BREVO_SMTP_PORT

        if not smtp_server or not smtp_user:
            print(f"[DEMO EMAIL] To: {to_email} | Subject: {subject}")
            return False

        msg = MIMEText(body_html, 'html')
        msg['Subject'] = subject
        msg['From'] = settings.SENDER_EMAIL or smtp_user
        msg['To'] = to_email

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[EMAIL DISPATCH ERROR] {e}")
        return False

@router.get("/register", response_class=HTMLResponse)
async def register_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Register - Effutu Municipal Library</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <i class="fa-solid fa-book-bookmark text-4xl text-emerald-600 mb-2"></i>
                <h2 class="text-2xl font-extrabold text-slate-800">Effutu Library Enrollment</h2>
                <p class="text-xs text-slate-500">Auto-Approval via Official Ghana Card Verification</p>
            </div>
            <form method="post" action="/auth/register" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Full Name</label>
                    <input name="full_name" placeholder="e.g. Kwame Mensah" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input name="email" type="email" placeholder="kwame@gmail.com" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Ghana Card Number</label>
                    <input name="ghana_card_number" placeholder="GHA-123456789-1" required pattern="GHA-[0-9]{9}-[0-9]{1}" class="w-full text-sm font-mono border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none uppercase">
                    <small class="text-[11px] text-slate-400">Required Format: GHA-123456789-1</small>
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Preferred Home Branch ID</label>
                    <input name="branch_id" type="number" value="1" placeholder="Branch ID" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Enroll with Ghana Card
                </button>
            </form>
            <div class="text-center pt-2 border-t border-slate-100">
                <a href="/auth/login" class="text-xs text-emerald-700 hover:underline font-semibold">Already have an account? Sign In</a>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    ghana_card_number: str = Form(...),
    branch_id: int = Form(1),
    db: Session = Depends(get_db)
):
    email_clean = email.lower().strip()
    card_clean = ghana_card_number.upper().strip()

    # Validate Ghana Card format
    if not re.match(r'^GHA-\d{9}-\d{1}$', card_clean):
        return HTMLResponse("""
        <div style='max-width:500px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Invalid Ghana Card Format</h3>
            <p>Correct format is <b>GHA-123456789-1</b></p>
            <a href='/auth/register' style='color:#2563eb;'>← Back to Registration</a>
        </div>
        """, status_code=400)

    if db.query(User).filter(User.email == email_clean).first():
        return HTMLResponse("""
        <div style='max-width:500px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Email Already Registered</h3>
            <p>An account with this email address already exists.</p>
            <a href='/auth/register' style='color:#2563eb;'>← Back to Registration</a>
        </div>
        """, status_code=400)

    if db.query(User).filter(User.ghana_card_number == card_clean).first():
        return HTMLResponse("""
        <div style='max-width:500px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Ghana Card Already Registered</h3>
            <p>This Ghana Card is already associated with an account. Only one account is permitted per Ghana Card.</p>
            <a href='/auth/register' style='color:#2563eb;'>← Back to Registration</a>
        </div>
        """, status_code=400)

    # Generate default password
    default_password = f"Effutu@{random.randint(1000, 9999)}"
    member_num = random.randint(1000, 9999)
    member_id = f"EFF-MBR-{member_num}"

    user = User(
        full_name=full_name.strip(),
        email=email_clean,
        ghana_card_number=card_clean,
        member_id=member_id,
        hashed_password=get_password_hash(default_password),
        branch_id=branch_id,
        role="patron",
        is_approved=True,
        is_active=True,
        must_change_password=True,
        is_physically_verified=False
    )
    db.add(user)
    db.commit()

    base_url = str(request.base_url).rstrip('/')
    email_body = f"""
    <html><body style='font-family:Arial, sans-serif; line-height:1.6; color:#1e293b;'>
    <div style='max-width:600px; margin:0 auto; border:1px solid #cbd5e1; border-radius:8px; padding:24px; background:#ffffff;'>
        <h2 style='color:#15803d; margin-top:0;'>Effutu Municipal Library Network</h2>
        <p>Dear <b>{full_name}</b>,</p>
        <p>Welcome to the Effutu Municipal Library Network in Winneba, Central Region, Ghana!</p>
        <p>Your library account has been created and <b>automatically approved</b> following verification of your Ghana Card (<b>{card_clean[:4]}XXXXXX{card_clean[-3:]}</b>).</p>
        
        <div style='background:#f0fdf4; border:1px solid #86efac; border-radius:6px; padding:16px; margin:16px 0;'>
            <h4 style='margin:0 0 8px 0; color:#166534;'>Your Account Credentials:</h4>
            <p style='margin:4px 0;'><b>Member ID:</b> <font color='#15803d'>{member_id}</font></p>
            <p style='margin:4px 0;'><b>Login Email:</b> {email_clean}</p>
            <p style='margin:4px 0;'><b>Default Password:</b> <code style='font-size:16px; background:#dcfce7; padding:2px 6px; border-radius:4px;'>{default_password}</code></p>
        </div>

        <p><b>Next Steps:</b></p>
        <ol>
            <li>Log in at: <a href='{base_url}/auth/login'>{base_url}/auth/login</a></li>
            <li>You will be prompted to change your default password immediately.</li>
            <li>On your first visit to your branch library, please present your <b>physical Ghana Card</b> for final physical verification and collection of your library card.</li>
        </ol>
        <p style='color:#64748b; font-size:12px;'>For assistance, please visit any of the 19 Effutu municipal library branches.</p>
        <p>Warm regards,<br><b>Effutu Municipal Library Management</b></p>
    </div>
    </body></html>
    """
    send_email(email_clean, "Your Effutu Library Account - Default Password & Next Steps", email_body)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Registration Successful - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 text-center space-y-4">
            <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto text-3xl">✓</div>
            <h2 class="text-2xl font-extrabold text-slate-800">Registration Successful!</h2>
            <p class="text-sm text-slate-600">Your account is auto-approved via Ghana Card validation.</p>
            
            <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-left font-mono text-xs space-y-1">
                <div><strong>Member ID:</strong> {member_id}</div>
                <div><strong>Email:</strong> {email_clean}</div>
                <div><strong>Default Password:</strong> <span class="bg-emerald-200 px-2 py-0.5 rounded text-emerald-900 font-bold">{default_password}</span></div>
            </div>

            <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 text-left">
                <strong>Important:</strong> Present your physical Ghana Card on your first library visit for physical verification and card issuance.
            </div>

            <a href="/auth/login" class="block w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow text-sm transition">
                Proceed to Login →
            </a>
        </div>
    </body>
    </html>
    """)

@router.get("/login", response_class=HTMLResponse)
async def login_page(msg: str = None):
    msg_banner = ""
    if msg == "password_changed_login_again":
        msg_banner = "<div class='bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs p-3 rounded-lg text-center mb-4 font-semibold'>Password updated successfully! Please log in with your new password.</div>"
    elif msg == "password_reset_success":
        msg_banner = "<div class='bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs p-3 rounded-lg text-center mb-4 font-semibold'>Password reset successful! You can now log in.</div>"

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Effutu Municipal Library</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <i class="fa-solid fa-book-bookmark text-4xl text-emerald-600 mb-2"></i>
                <h2 class="text-2xl font-extrabold text-slate-800">Effutu Library Sign In</h2>
                <p class="text-xs text-slate-500">Access Municipal Library System & AI Tools</p>
            </div>

            {msg_banner}

            <form method="post" action="/auth/login" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input name="email" type="email" placeholder="kwame@gmail.com" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Password</label>
                    <input type="password" name="password" placeholder="••••••••" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                    <div class="text-right mt-1">
                        <a href="/auth/forgot-password" class="text-xs text-blue-600 hover:underline">Forgot Password?</a>
                    </div>
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Sign In to Account
                </button>
            </form>
            <div class="text-center pt-2 border-t border-slate-100">
                <a href="/auth/register" class="text-xs text-emerald-700 hover:underline font-semibold">Register with Ghana Card →</a>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return HTMLResponse("""
        <div style='max-width:400px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Invalid Credentials</h3>
            <p>Incorrect email address or password.</p>
            <a href='/auth/login' style='color:#2563eb;'>← Back to Login</a>
        </div>
        """, status_code=400)

    if not user.is_active:
        return HTMLResponse("""
        <div style='max-width:400px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Account Deactivated</h3>
            <p>Your library account has been deactivated by the branch librarian. Please contact your local library desk.</p>
            <a href='/auth/login' style='color:#2563eb;'>← Back to Login</a>
        </div>
        """, status_code=403)

    token = create_access_token({"sub": str(user.id), "role": user.role})

    # Redirect to force password change if required
    if user.must_change_password:
        temp_token = create_access_token({"sub": str(user.id), "type": "force_change"}, expires_delta=timedelta(minutes=30))
        resp = RedirectResponse(url=f"/auth/force-change-password?token={temp_token}", status_code=303)
        resp.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
        return resp

    redirect_url = f"/dashboard/{user.role}" if user.role in ["sys_admin", "hq_admin", "librarian", "patron"] else "/dashboard/patron"
    resp = RedirectResponse(url=redirect_url, status_code=303)
    resp.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return resp

@router.get("/force-change-password", response_class=HTMLResponse)
async def force_change_page(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "force_change":
            raise Exception()
    except Exception:
        return HTMLResponse("""
        <div style='max-width:400px; margin:50px auto; font-family:sans-serif; text-align:center;'>
            <h3>Invalid or Expired Token</h3>
            <a href='/auth/login'>Back to Login</a>
        </div>
        """, status_code=400)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Change Default Password - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <h2 class="text-2xl font-extrabold text-slate-800">Change Default Password</h2>
                <p class="text-xs text-amber-600 font-medium">You must change your default password before continuing.</p>
            </div>
            <form method="post" action="/auth/force-change-password?token={token}" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">New Password (min 6 chars)</label>
                    <input type="password" name="new_password" required minlength="6" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Confirm New Password</label>
                    <input type="password" name="confirm_password" required minlength="6" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Update Password & Continue →
                </button>
            </form>
        </div>
    </body>
    </html>
    """)

@router.post("/force-change-password", response_class=HTMLResponse)
async def force_change_post(
    token: str,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if new_password != confirm_password:
        return HTMLResponse("<h3>Passwords do not match</h3><a href='javascript:history.back()'>Back</a>", status_code=400)
    if len(new_password) < 6:
        return HTMLResponse("<h3>Password must be at least 6 characters</h3><a href='javascript:history.back()'>Back</a>", status_code=400)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "force_change":
            raise Exception()
        user_id = int(payload.get("sub"))
    except Exception:
        return HTMLResponse("<h3>Invalid or expired token</h3><a href='/auth/login'>Login</a>", status_code=400)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse("<h3>User not found</h3>", status_code=400)

    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse(url="/auth/login?msg=password_changed_login_again", status_code=303)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Forgot Password - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <h2 class="text-2xl font-extrabold text-slate-800">Forgot Password</h2>
                <p class="text-xs text-slate-500">Enter your registered email to receive a password reset link.</p>
            </div>
            <form method="post" action="/auth/forgot-password" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input name="email" type="email" placeholder="kwame@gmail.com" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow transition">
                    Send Password Reset Link
                </button>
            </form>
            <div class="text-center pt-2">
                <a href="/auth/login" class="text-xs text-slate-600 hover:underline">← Back to Login</a>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_post(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    reset_link_html = ""
    if user:
        token = create_access_token({"sub": str(user.id), "type": "reset"}, expires_delta=timedelta(minutes=15))
        base_url = str(request.base_url).rstrip('/')
        reset_link = f"{base_url}/auth/reset-password?token={token}"
        
        email_body = f"""
        <p>Dear {user.full_name},</p>
        <p>You requested a password reset for your Effutu Municipal Library account.</p>
        <p><a href='{reset_link}'>Click here to reset your password</a></p>
        <p>Link: {reset_link}</p>
        <p>This link expires in 15 minutes.</p>
        """
        send_email(user.email, "Effutu Library - Password Reset Request", email_body)
        reset_link_html = f"<div style='margin-top:15px; padding:12px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; font-size:13px;'><b>Demo Link:</b> <a href='{reset_link}' style='word-break:break-all;'>{reset_link}</a></div>"

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Reset Link Sent - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 text-center space-y-4">
            <h2 class="text-xl font-extrabold text-slate-800">Password Reset Requested</h2>
            <p class="text-xs text-slate-600">If an account exists for {email}, a reset link has been dispatched.</p>
            {reset_link_html}
            <a href="/auth/login" class="inline-block px-4 py-2 bg-emerald-700 text-white font-bold rounded-lg text-xs">Return to Login</a>
        </div>
    </body>
    </html>
    """)

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_page(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "reset":
            raise Exception()
    except Exception:
        return HTMLResponse("""
        <div style='max-width:400px; margin:50px auto; font-family:sans-serif; text-align:center;'>
            <h3>Invalid or Expired Reset Token</h3>
            <a href='/auth/forgot-password'>Request New Reset Link</a>
        </div>
        """, status_code=400)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Reset Password - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <h2 class="text-2xl font-extrabold text-slate-800 text-center">Reset Password</h2>
            <form method="post" action="/auth/reset-password?token={token}" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">New Password</label>
                    <input type="password" name="new_password" required minlength="6" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Set New Password
                </button>
            </form>
        </div>
    </body>
    </html>
    """)

@router.post("/reset-password", response_class=HTMLResponse)
async def reset_post(
    token: str,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "reset":
            raise Exception()
        user_id = int(payload.get("sub"))
    except Exception:
        return HTMLResponse("<h3>Invalid or expired token</h3><a href='/auth/forgot-password'>Try again</a>", status_code=400)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse("<h3>User not found</h3>", status_code=400)

    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse(url="/auth/login?msg=password_reset_success", status_code=303)

@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/auth/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp
