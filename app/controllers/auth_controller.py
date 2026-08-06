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
async def register_page(db: Session = Depends(get_db)):
    from app.models import Branch
    branches = db.query(Branch).filter(Branch.status == "active").all()
    branch_options = ""
    if branches:
        for b in branches:
            branch_options += f'<option value="{b.id}">{b.name} ({b.location})</option>'
    else:
        branch_options = """
        <option value="1">Effutu Main Library - Winneba</option>
        <option value="2">Effutu UME Library</option>
        <option value="3">Effutu School Library</option>
        <option value="4">Nsakyir Library</option>
        <option value="5">Gyahadze Community Library</option>
        """

    return HTMLResponse(f"""
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
                <p class="text-xs text-slate-500">Join the Municipal Library Network</p>
            </div>
            <form method="post" action="/auth/register" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Select Your Library *</label>
                    <select name="branch_id" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white focus:border-emerald-600 focus:outline-none">
                        <option value="">-- Choose Library --</option>
                        {branch_options}
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ID Type *</label>
                    <select name="id_type" id="id_type" onchange="toggleIdField()" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 bg-white focus:border-emerald-600 focus:outline-none">
                        <option value="">-- Select ID Type --</option>
                        <option value="ghanacard">Ghana Card</option>
                        <option value="voters">Voters ID</option>
                        <option value="school_id">School ID</option>
                        <option value="not_available">Card not available at the moment</option>
                    </select>
                </div>
                <div id="id_number_div">
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ID Number *</label>
                    <input type="text" name="id_number" id="id_number" placeholder="Enter ID number" class="w-full text-sm font-mono border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div id="no_card_div" style="display:none;">
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Guardian Phone / School Name *</label>
                    <input type="text" name="alt_contact" id="alt_contact" placeholder="Enter guardian phone or school name for verification" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                    <p class="text-[12px] text-amber-600 font-semibold mt-1">You will need to present your ID on first visit to library</p>
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Full Name *</label>
                    <input name="full_name" placeholder="e.g. Kwame Mensah" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Phone Number *</label>
                    <input name="phone" type="tel" placeholder="024XXXXXXX" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input name="email" type="email" placeholder="kwame@gmail.com" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Password *</label>
                    <input name="password" type="password" placeholder="••••••••" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Complete Registration
                </button>
            </form>
            <div class="text-center pt-2 border-t border-slate-100">
                <a href="/auth/login" class="text-xs text-emerald-700 hover:underline font-semibold">Already have an account? Sign In</a>
            </div>
        </div>
        <script>
        function toggleIdField() {{
            const idType = document.getElementById('id_type').value;
            const idDiv = document.getElementById('id_number_div');
            const noCardDiv = document.getElementById('no_card_div');
            const idInput = document.getElementById('id_number');
            const altInput = document.getElementById('alt_contact');
            
            if (idType === 'not_available') {{
                idDiv.style.display = 'none';
                noCardDiv.style.display = 'block';
                idInput.required = false;
                if (altInput) altInput.required = true;
            }} else {{
                idDiv.style.display = 'block';
                noCardDiv.style.display = 'none';
                idInput.required = true;
                if (altInput) altInput.required = false;
                
                if (idType === 'ghanacard') idInput.placeholder = 'GHA-XXXXXXXXX-X';
                else if (idType === 'voters') idInput.placeholder = 'Enter Voters ID number';
                else if (idType === 'school_id') idInput.placeholder = 'Enter School ID number';
                else idInput.placeholder = 'Enter ID number';
            }}
        }}
        </script>
    </body>
    </html>
    """)

@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    password: str = Form(...),
    branch_id: int = Form(1),
    id_type: str = Form("ghanacard"),
    id_number: str = Form(""),
    alt_contact: str = Form(""),
    db: Session = Depends(get_db)
):
    wants_json = "application/json" in request.headers.get("accept", "").lower()
    email_clean = email.lower().strip() if email else f"{phone.strip()}@effutulibrary.org"
    phone_clean = phone.strip()
    id_number_clean = id_number.strip() if id_number else None
    alt_contact_clean = alt_contact.strip() if alt_contact else None

    # Duplicate Checks
    if email_clean and db.query(User).filter(User.email == email_clean).first():
        msg = "An account with this email address already exists."
        if wants_json: return JSONResponse(status_code=400, content={"error": msg})
        return HTMLResponse(f"<h3>{msg}</h3><a href='/auth/register'>Back</a>", status_code=400)

    if phone_clean and db.query(User).filter(User.phone == phone_clean).first():
        msg = "An account with this phone number already exists."
        if wants_json: return JSONResponse(status_code=400, content={"error": msg})
        return HTMLResponse(f"<h3>{msg}</h3><a href='/auth/register'>Back</a>", status_code=400)

    ghana_card = id_number_clean.upper() if (id_type == "ghanacard" and id_number_clean) else None
    if ghana_card and db.query(User).filter(User.ghana_card_number == ghana_card).first():
        msg = "This Ghana Card is already registered with an account."
        if wants_json: return JSONResponse(status_code=400, content={"error": msg})
        return HTMLResponse(f"<h3>{msg}</h3><a href='/auth/register'>Back</a>", status_code=400)

    member_num = random.randint(1000, 9999)
    member_id = f"EFF-MBR-{member_num}"
    verification_status = "pending" if id_type == "not_available" else "verified"

    user = User(
        full_name=full_name.strip(),
        email=email_clean,
        phone=phone_clean,
        ghana_card_number=ghana_card,
        id_type=id_type,
        id_number=id_number_clean,
        alt_contact=alt_contact_clean,
        verification_status=verification_status,
        member_id=member_id,
        hashed_password=get_password_hash(password),
        branch_id=branch_id,
        role="patron",
        is_approved=True,
        is_active=True,
        must_change_password=False,
        is_physically_verified=(id_type != "not_available")
    )
    db.add(user)
    db.commit()

    if wants_json:
        return JSONResponse(content={"message": "Registration successful! You can now log in.", "member_id": member_id})

    return RedirectResponse(url="/auth/login?msg=registration_success", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_page(msg: str = None):
    msg_banner = ""
    if msg == "password_changed_login_again":
        msg_banner = "<div class='bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs p-3 rounded-lg text-center mb-4 font-semibold'>Password updated successfully! Please log in with your new password.</div>"
    elif msg == "password_reset_success":
        msg_banner = "<div class='bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs p-3 rounded-lg text-center mb-4 font-semibold'>Password reset successful! You can now log in.</div>"
    elif msg == "registration_success":
        msg_banner = "<div class='bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs p-3 rounded-lg text-center mb-4 font-semibold'>Registration successful! Please log in with your credentials.</div>"

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
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Ghana Card / Voter ID / School ID / Email / Phone</label>
                    <input name="email" type="text" placeholder="GHA-XXXXXXXXX-X, Email, or Phone" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
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
                <a href="/auth/register" class="text-xs text-emerald-700 hover:underline font-semibold">Don't have account? Register here</a>
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
    wants_json = "application/json" in request.headers.get("accept", "").lower()
    identifier_clean = email.strip()

    # Search user across email, ghana_card_number, id_number, phone, or member_id
    user = db.query(User).filter(
        (User.email == identifier_clean.lower()) |
        (User.ghana_card_number == identifier_clean.upper()) |
        (User.id_number == identifier_clean) |
        (User.phone == identifier_clean) |
        (User.member_id == identifier_clean.upper())
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        if wants_json:
            return JSONResponse(status_code=400, content={"error": "Invalid ID, email, phone, or password."})
        return HTMLResponse("""
        <div style='max-width:400px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:20px; border-radius:8px; background:#fef2f2;'>
            <h3 style='color:#dc2626;'>Invalid Credentials</h3>
            <p>Incorrect ID, email, phone, or password.</p>
            <a href='/auth/login' style='color:#2563eb;'>← Back to Login</a>
        </div>
        """, status_code=400)

    if not user.is_active:
        if wants_json:
            return JSONResponse(status_code=403, content={"error": "Account deactivated by librarian."})
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
        target_url = f"/auth/force-change-password?token={temp_token}"
        if wants_json:
            resp = JSONResponse(content={"redirect_url": target_url})
        else:
            resp = RedirectResponse(url=target_url, status_code=303)
        resp.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
        return resp

    redirect_url = f"/dashboard/{user.role}" if user.role in ["sys_admin", "hq_admin", "librarian", "patron"] else "/dashboard/patron"
    if wants_json:
        resp = JSONResponse(content={"redirect_url": redirect_url})
    else:
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

@router.get("/reset-admin")
def reset_admin_credentials():
    import traceback
    from sqlalchemy import text
    from app.database import engine, SessionLocal

    migration_logs = []

    # 1. Execute Schema Migration in Isolated Raw Engine Connections
    statements = [
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='ghana_card_number') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='ghana_card') THEN
                    ALTER TABLE users RENAME COLUMN ghana_card TO ghana_card_number;
                ELSE
                    ALTER TABLE users ADD COLUMN ghana_card_number VARCHAR(50);
                END IF;
            END IF;
        END $$;
        """,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ghana_card_number VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_physically_verified BOOLEAN DEFAULT FALSE;"
    ]

    for stmt in statements:
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
                migration_logs.append(f"Executed: {stmt.strip()[:45]}...")
        except Exception as st_err:
            migration_logs.append(f"Handled: {str(st_err)[:60]}")

    # 2. Open Fresh Session and Seed / Reset Admin Credentials
    db = SessionLocal()
    try:
        creds = [
            ("admin@effutu.edu.gh", "sys_admin", "Admin@123", "GHA-000000000-0"),
            ("librarian@effutu.edu.gh", "librarian", "Librarian@123", "GHA-000000001-0"),
            ("sysadmin@effutulibrary.gov.gh", "sys_admin", "admin123", "GHA-000000001-1"),
            ("librarian@effutulibrary.gov.gh", "librarian", "admin123", "GHA-000000003-3")
        ]
        result = []
        for email, role, plain, gha in creds:
            user = db.query(User).filter(User.email == email).first()
            hashed = get_password_hash(plain)
            if not user:
                user = User(
                    email=email,
                    full_name=role.replace('_', ' ').title(),
                    role=role,
                    ghana_card_number=gha,
                    is_approved=True,
                    is_active=True,
                    must_change_password=False,
                    is_physically_verified=True,
                    hashed_password=hashed
                )
                db.add(user)
                result.append(f"Created {email} / {plain}")
            else:
                user.hashed_password = hashed
                user.is_active = True
                user.is_approved = True
                user.must_change_password = False
                user.is_physically_verified = True
                user.ghana_card_number = gha
                db.commit()
                result.append(f"Reset {email} / {plain}")
        db.commit()
        db.close()
        return {
            "status": "success",
            "schema_migration": migration_logs,
            "details": result,
            "login_now": "Use admin@effutu.edu.gh / Admin@123 or librarian@effutu.edu.gh / Librarian@123"
        }
    except Exception as e:
        db.rollback()
        db.close()
        return {
            "status": "error",
            "schema_migration": migration_logs,
            "error": str(e),
            "trace": traceback.format_exc()
        }



