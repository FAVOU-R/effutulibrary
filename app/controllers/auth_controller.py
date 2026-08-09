from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.config import settings
from jose import jwt
import hashlib, re, os, random, uuid
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_password_hash(p: str) -> str:
    """Hash password using direct bcrypt with 12 rounds of dynamic salting"""
    try:
        import bcrypt
        pw_bytes = p.encode('utf-8')[:72]
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')
    except Exception as e:
        print(f"Bcrypt hash fallback: {e}")
        salt = "effutu_ghana_salt_2026"
        return hashlib.sha256(f"{p}{salt}".encode('utf-8')).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password supporting bcrypt hashes ($2b$) and legacy SHA-256 hashes"""
    if not plain or not hashed:
        return False
    if hashed.startswith("$2b$") or hashed.startswith("$2a$") or hashed.startswith("$2y$"):
        try:
            import bcrypt
            pw_bytes = plain.encode('utf-8')[:72]
            return bcrypt.checkpw(pw_bytes, hashed.encode('utf-8'))
        except Exception as e:
            print(f"Bcrypt verify error: {e}")
            return False
    salt = "effutu_ghana_salt_2026"
    return hashlib.sha256(f"{plain}{salt}".encode('utf-8')).hexdigest() == hashed

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

from app.services.email_service import send_email, send_email_sync

@router.get("/test-email")
async def test_email_endpoint(to: str):
    """Diagnostic endpoint to test Brevo SMTP email dispatch"""
    if not to or "@" not in to:
        return JSONResponse(status_code=400, content={"error": "Invalid email. Pass ?to=your_email@gmail.com"})
    
    success = send_email_sync(to, "Effutu Library Brevo Test", "<h3>Brevo Port 2525 Email Test</h3><p>Your Brevo configuration is working perfectly!</p>")
    if success:
        return {"success": True, "message": f"Brevo test email sent successfully to {to} via Port 2525."}
    else:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "Failed to send Brevo email. Please check server logs or ensure BREVO_SMTP_KEY is set in Render Environment Variables."
        })

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
    username: str = Form(""),
    email: str = Form(""),
    phone: str = Form(...),
    password: str = Form(...),
    branch_id: int = Form(1),
    id_type: str = Form("ghanacard"),
    id_number: str = Form(""),
    alt_contact: str = Form(""),
    sex: str = Form("Male"),
    school_occupation: str = Form(""),
    location: str = Form(""),
    id_photo: UploadFile = File(None),
    guardian_name: str = Form(""),
    guardian_phone: str = Form(""),
    guardian_email: str = Form(""),
    guardian_relationship: str = Form("Guardian"),
    db: Session = Depends(get_db)
):
    from app.models import Branch
    wants_json = "application/json" in request.headers.get("accept", "").lower()
    email_clean = email.lower().strip() if email.strip() else None
    phone_clean = phone.strip()
    id_number_clean = id_number.strip() if id_number.strip() else None
    alt_contact_clean = alt_contact.strip() if alt_contact.strip() else None
    username_clean = username.strip().lower().lstrip('@') if username.strip() else None

    # Handle optional ID Photo upload
    id_photo_url = None
    if id_photo and id_photo.filename:
        try:
            upload_dir = os.path.join("app", "static", "uploads", "id_photos")
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{id_photo.filename.replace(' ', '_')}"
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await id_photo.read())
            id_photo_url = f"/static/uploads/id_photos/{filename}"
        except Exception as e:
            print(f"ID photo upload warning: {e}")

    # Password validation check
    from app.config import settings
    if len(password) < getattr(settings, "MIN_PASSWORD_LENGTH", 6):
        msg = f"Password must be at least {getattr(settings, 'MIN_PASSWORD_LENGTH', 6)} characters long."
        if wants_json: return JSONResponse(status_code=400, content={"error": msg})
        return HTMLResponse(f"<h3>{msg}</h3><a href='/auth/register'>Back</a>", status_code=400)

    # Username validation & auto-generation
    import re
    if username_clean:
        if db.query(User).filter(User.username == username_clean).first():
            msg = f"The username '@{username_clean}' is already taken. Please choose a different username."
            if wants_json: return JSONResponse(status_code=400, content={"error": msg})
            return HTMLResponse(f"<h3>{msg}</h3><a href='/auth/register'>Back</a>", status_code=400)
        final_username = username_clean
    else:
        # Auto-generate username from full_name or email
        if email_clean:
            base_handle = email_clean.split("@")[0].lower()
        else:
            base_handle = full_name.strip().lower().replace(" ", "_")
        
        base_handle = re.sub(r'[^a-z0-9_]', '', base_handle)
        if not base_handle:
            base_handle = f"patron_{random.randint(100, 999)}"
            
        candidate = base_handle
        counter = 1
        while db.query(User).filter(User.username == candidate).first():
            candidate = f"{base_handle}{counter}"
            counter += 1
        final_username = candidate

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
    member_id = f"EFL-{member_num}"
    verification_status = "pending"  # Default status for new patron enrollment

    user = User(
        full_name=full_name.strip(),
        username=final_username,
        email=email_clean,
        phone=phone_clean,
        ghana_card_number=ghana_card,
        id_type=id_type,
        id_number=id_number_clean,
        alt_contact=alt_contact_clean,
        sex=sex.strip(),
        school_occupation=school_occupation.strip() if school_occupation else None,
        location=location.strip() if location else None,
        id_photo_url=id_photo_url,
        guardian_name=guardian_name.strip() if guardian_name else None,
        guardian_phone=guardian_phone.strip() if guardian_phone else None,
        guardian_email=guardian_email.lower().strip() if guardian_email else None,
        guardian_relationship=guardian_relationship.strip() if guardian_relationship else None,
        verification_status=verification_status,
        member_id=member_id,
        hashed_password=get_password_hash(password),
        branch_id=branch_id,
        role="patron",
        is_approved=True,
        is_active=True,
        must_change_password=False,
        is_physically_verified=False
    )
    db.add(user)
    db.commit()

    # Send Welcome Email (Non-blocking)
    try:
        br = db.query(Branch).filter(Branch.id == branch_id).first()
        branch_name = br.name if br else "Effutu Municipal Library Network"
        
        if email_clean:
            welcome_html = f"<h3>Akwaaba {full_name.strip()}!</h3><p>Registered at {branch_name}. Code: <b>{member_id}</b>. Visit library with ID for verification.</p><p>Effutu Library Network</p>"
            send_email(email_clean, f"Akwaaba {full_name.strip()}! - Effutu Library", welcome_html)
        
        if guardian_email and guardian_email.strip():
            parent_html = f"<p>Hello, your child <b>{full_name.strip()}</b> registered at Effutu Library ({branch_name}). Code: <b>{member_id}</b></p>"
            send_email(guardian_email.strip(), f"Effutu Library Network - Child Registration Notice", parent_html)
    except Exception as ex:
        print(f"[REGISTRATION EMAIL DISPATCH WARNING] {ex}")

    if wants_json:
        return JSONResponse(content={"message": "Registration successful! Account awaiting verification.", "member_id": member_id})

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
        <title>Sign In - Effutu Municipal Library Network</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }}
        </style>
    </head>
    <body class="bg-gradient-to-br from-slate-900 via-emerald-950 to-slate-900 min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
        <div class="absolute -top-32 -left-32 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div class="max-w-md w-full bg-white/95 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl p-8 space-y-6 relative z-10">
            <div class="text-center space-y-2">
                <div class="inline-flex items-center justify-center w-14 h-14 bg-emerald-700 text-white rounded-2xl shadow-lg shadow-emerald-700/30 mb-1">
                    <i class="fa-solid fa-book-open-reader text-2xl"></i>
                </div>
                <h1 class="text-2xl font-extrabold text-slate-900 tracking-tight">Effutu Library Sign In</h1>
                <p class="text-xs text-slate-500 font-medium">Access your municipal library portal & resources</p>
            </div>

            {msg_banner}

            <form method="post" action="/auth/login" class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                        Account Identifier
                    </label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            <i class="fa-solid fa-user text-sm"></i>
                        </div>
                        <input name="email" type="text" placeholder="Email, Phone, Ghana Card, or Member ID" required
                            class="w-full pl-10 pr-3.5 py-3 text-sm bg-slate-50/80 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:bg-white focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 focus:outline-none transition">
                    </div>
                </div>

                <div>
                    <div class="flex items-center justify-between mb-1.5">
                        <label class="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                            Password
                        </label>
                        <a href="/auth/forgot-password" class="text-xs text-emerald-700 hover:text-emerald-800 font-semibold transition">
                            Forgot Password?
                        </a>
                    </div>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            <i class="fa-solid fa-lock text-sm"></i>
                        </div>
                        <input id="password-input" type="password" name="password" placeholder="••••••••" required
                            class="w-full pl-10 pr-10 py-3 text-sm bg-slate-50/80 border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 focus:bg-white focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 focus:outline-none transition">
                        <button type="button" onclick="togglePasswordVisibility()" class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600">
                            <i id="password-toggle-icon" class="fa-solid fa-eye text-sm"></i>
                        </button>
                    </div>
                </div>

                <button type="submit" class="w-full py-3.5 bg-gradient-to-r from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-700/25 hover:shadow-emerald-700/40 active:scale-[0.99] transition duration-200 flex items-center justify-center gap-2">
                    <span>Sign In to Account</span>
                    <i class="fa-solid fa-arrow-right text-xs"></i>
                </button>
            </form>

            <div class="pt-4 border-t border-slate-200/80 text-center">
                <p class="text-xs text-slate-500 font-medium">
                    Don't have an account? 
                    <a href="/auth/register" class="text-emerald-700 hover:text-emerald-800 font-bold hover:underline ml-1">
                        Register Here
                    </a>
                </p>
            </div>
        </div>

        <script>
        function togglePasswordVisibility() {{
            const input = document.getElementById('password-input');
            const icon = document.getElementById('password-toggle-icon');
            if (input.type === 'password') {{
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }} else {{
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }}
        }}
        </script>
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

    try:
        # Search user across email, username, ghana_card_number, id_number, phone, or member_id
        user = db.query(User).filter(
            (User.email == identifier_clean.lower()) |
            (User.username == identifier_clean.lower().lstrip('@')) |
            (User.ghana_card_number == identifier_clean.upper()) |
            (User.id_number == identifier_clean) |
            (User.phone == identifier_clean) |
            (User.member_id == identifier_clean.upper())
        ).first()

        if user:
            now = datetime.utcnow()
            # Check if user account is currently locked out
            if getattr(user, "locked_until", None) and user.locked_until > now:
                mins_left = max(1, int((user.locked_until - now).total_seconds() / 60) + 1)
                msg = f"🔒 Account temporarily locked due to successive bad password attempts. Please try again in {mins_left} minute(s) or reset your password."
                if wants_json:
                    return JSONResponse(status_code=429, content={"error": msg})
                return HTMLResponse(f"""
                <div style='max-width:450px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:24px; border-radius:12px; background:#fff5f5;'>
                    <h3 style='color:#dc2626;'>🚨 Account Temporarily Locked</h3>
                    <p style='color:#4b5563; font-size:14px;'>Your account is temporarily locked for <b>{mins_left} minute(s)</b> due to successive bad password attempts.</p>
                    <p style='font-size:12px; color:#6b7280;'>A security alert email has been dispatched to your registered email address.</p>
                    <div style='margin-top:15px;'>
                        <a href='/auth/forgot-password' style='display:inline-block; padding:8px 16px; background:#dc2626; color:white; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px;'>Reset Password Now</a>
                        <a href='/auth/login' style='display:inline-block; margin-left:8px; color:#2563eb; font-size:12px;'>← Back to Login</a>
                    </div>
                </div>
                """, status_code=429)

        # Password check
        if not user or not verify_password(password, user.hashed_password):
            if user:
                try:
                    user.failed_login_attempts = getattr(user, "failed_login_attempts", 0) + 1
                    max_attempts = getattr(settings, "MAX_FAILED_LOGIN_ATTEMPTS", 5)
                    lockout_mins = getattr(settings, "ACCOUNT_LOCKOUT_MINUTES", 15)

                    if user.failed_login_attempts >= max_attempts:
                        user.locked_until = datetime.utcnow() + timedelta(minutes=lockout_mins)
                        user.failed_login_attempts = 0
                        db.commit()

                        # Dispatch Email Notification
                        if user.email:
                            email_body = f"""
                            <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #fca5a5; border-radius: 12px; background: #fff5f5;">
                                <h2 style="color: #dc2626;">🚨 Security Alert: Account Temporarily Locked</h2>
                                <p>Akwaaba <b>{user.full_name}</b>,</p>
                                <p>Your Effutu Municipal Library account (ID: <b>{user.member_id or user.email}</b>) has been <b>temporarily locked for {lockout_mins} minutes</b> due to <b>{max_attempts} consecutive bad password attempts</b>.</p>
                                <div style="background-color: #fef2f2; padding: 14px; border-left: 4px solid #ef4444; margin: 15px 0; font-size: 13px;">
                                    <b>Lockout Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                                    <b>Lockout Duration:</b> {lockout_mins} minutes<br>
                                    <b>Reason:</b> Successive Bad Password Attempts
                                </div>
                                <p style="font-size: 13px; color: #374151;"><b>If this was you:</b> You can wait for the {lockout_mins}-minute timer to expire or reset your password using the button below.</p>
                                <p style="font-size: 13px; color: #b91c1c; font-weight: bold;">If this was NOT you attempting to sign in:</p>
                                <p style="font-size: 12px; color: #4b5563;">Someone may be attempting to gain unauthorized access to your account. We strongly advise resetting your password immediately or contacting your local branch librarian.</p>
                                <div style="margin-top: 20px;">
                                    <a href="https://effutu-library-system.onrender.com/auth/forgot-password" style="background-color: #dc2626; color: white; padding: 10px 18px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 13px;">Reset Password Now</a>
                                </div>
                                <hr style="border: none; border-top: 1px solid #fee2e2; margin: 20px 0;">
                                <p style="font-size: 11px; color: #9ca3af;">Effutu Municipal Library Network • Security & Protection Desk</p>
                            </div>
                            """
                            send_email(user.email, "🚨 Security Alert: Account Temporarily Locked (Failed Login Attempts)", email_body)

                        msg = f"🔒 Account temporarily locked due to {max_attempts} successive bad password attempts. A security alert email has been sent to your address."
                        if wants_json:
                            return JSONResponse(status_code=429, content={"error": msg})
                        return HTMLResponse(f"""
                        <div style='max-width:450px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:24px; border-radius:12px; background:#fff5f5;'>
                            <h3 style='color:#dc2626;'>🚨 Account Temporarily Locked</h3>
                            <p style='color:#4b5563; font-size:14px;'>Your account has been locked for <b>{lockout_mins} minutes</b> due to successive bad password attempts.</p>
                            <p style='font-size:12px; color:#047857; font-weight:bold;'>An email alert was sent to your registered address just in case you were not the one trying to log in.</p>
                            <div style='margin-top:15px;'>
                                <a href='/auth/forgot-password' style='display:inline-block; padding:8px 16px; background:#dc2626; color:white; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px;'>Reset Password Now</a>
                                <a href='/auth/login' style='display:inline-block; margin-left:8px; color:#2563eb; font-size:12px;'>← Back to Login</a>
                            </div>
                        </div>
                        """, status_code=429)
                    else:
                        db.commit()
                except Exception as ex:
                    print(f"Failed attempts tracking exception: {ex}")
                    db.rollback()

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

        # Successful login: reset failed attempts & lockout timestamp
        try:
            if getattr(user, "failed_login_attempts", None) or getattr(user, "locked_until", None):
                user.failed_login_attempts = 0
                user.locked_until = None
                db.commit()
        except Exception as ex:
            print(f"Lockout reset warning: {ex}")
            db.rollback()

        token = create_access_token({"sub": str(user.id), "role": user.role})

        # Redirect to force password change if required
        if getattr(user, "must_change_password", False):
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

    except Exception as e:
        db.rollback()
        print(f"[LOGIN PROCESS ERROR] Exception during authentication: {e}")
        if wants_json:
            return JSONResponse(status_code=400, content={"error": "Authentication processing error. Please try again."})
        return HTMLResponse(f"""
        <div style='max-width:450px; margin:50px auto; font-family:sans-serif; text-align:center; border:1px solid #fca5a5; padding:24px; border-radius:12px; background:#fff5f5;'>
            <h3 style='color:#dc2626;'>Login Error</h3>
            <p style='color:#4b5563; font-size:14px;'>An issue occurred while processing your sign in credentials. Please double check your details and try again.</p>
            <div style='margin-top:15px;'>
                <a href='/auth/login' style='display:inline-block; padding:8px 16px; background:#047857; color:white; border-radius:6px; text-decoration:none; font-weight:bold; font-size:12px;'>← Back to Login</a>
            </div>
        </div>
        """, status_code=400)


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
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">New Password (min 8 chars)</label>
                    <input type="password" name="new_password" required minlength="8" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Confirm New Password</label>
                    <input type="password" name="confirm_password" required minlength="8" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
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
    min_len = getattr(settings, "MIN_PASSWORD_LENGTH", 8)
    if new_password != confirm_password:
        return HTMLResponse("<h3>Passwords do not match</h3><a href='javascript:history.back()'>Back</a>", status_code=400)
    if len(new_password) < min_len:
        return HTMLResponse(f"<h3>Password must be at least {min_len} characters</h3><a href='javascript:history.back()'>Back</a>", status_code=400)
    
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

    if user.email:
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h2 style="color: #047857;">Security Notice: Password Updated</h2>
            <p>Akwaaba <b>{user.full_name}</b>,</p>
            <p>This email confirms that the password for your Effutu Municipal Library Network account was updated successfully.</p>
            <div style="background-color: #ecfdf5; padding: 12px; border-left: 4px solid #10b981; margin: 15px 0;">
                <b>Member ID:</b> {user.member_id or user.email}<br>
                <b>Security Status:</b> Password Update Completed Successfully
            </div>
            <p style="font-size: 12px; color: #b91c1c; font-weight: bold;">If you did NOT perform this change, please contact your branch librarian immediately to secure your account.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #64748b;">Effutu Municipal Library Network</p>
        </div>
        """
        send_email(user.email, "🔒 Security Alert: Your Password Was Changed - Effutu Library", email_body)

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
    if user:
        token = create_access_token({"sub": str(user.id), "type": "reset"}, expires_delta=timedelta(minutes=15))
        base_url = str(request.base_url).rstrip('/')
        reset_link = f"{base_url}/auth/reset-password?token={token}"
        
        email_body = f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; color: #1e293b;">
            <h2 style="color: #047857; margin-top: 0;">Password Reset Request 🔑</h2>
            <p>Akwaaba <b>{user.full_name}</b>,</p>
            <p>You requested a password reset for your <b>Effutu Municipal Library Network</b> account.</p>
            <p>Click the secure button below to choose a new password:</p>
            <div style="margin: 20px 0;">
                <a href='{reset_link}' style="background-color: #047857; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 8px; display: inline-block;">Reset Password Now</a>
            </div>
            <p style="font-size: 12px; color: #64748b;">Or copy this link into your browser: <br><a href='{reset_link}' style="color: #0284c7; word-break: break-all;">{reset_link}</a></p>
            <p style="font-size: 12px; color: #dc2626; margin-top: 16px;">This link is valid for 15 minutes. If you did not request a password reset, you can safely ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #94a3b8; text-align: center;">Effutu Municipal Library Network • Winneba, Ghana</p>
        </div>
        """
        send_email(user.email, "🔑 Password Reset Request — Effutu Municipal Library Network", email_body)

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
            <div class="inline-flex items-center justify-center w-12 h-12 bg-emerald-100 text-emerald-700 rounded-full mb-1">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
            </div>
            <h2 class="text-xl font-extrabold text-slate-800">Password Reset Email Dispatched</h2>
            <p class="text-xs text-slate-600 leading-relaxed">If an account exists for <strong class="text-slate-800">{email}</strong>, a secure password reset link has been sent directly to that inbox. Please check your email inbox and spam folder.</p>
            <div class="pt-2">
                <a href="/auth/login" class="inline-block px-5 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg text-xs shadow transition">← Return to Login</a>
            </div>
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
def reset_admin_credentials(
    secret: str = "",
    request: Request = None,
    db_session: Session = Depends(get_db)
):
    # Security Protection Check: Block unauthenticated public triggers
    expected_secret = os.getenv("ADMIN_RESET_SECRET", "effutu_emergency_reset_2026")
    current_user = get_current_user_optional(request, db_session) if request else None

    is_sys_admin = current_user and current_user.role == "sys_admin"
    is_valid_secret = secret and secret == expected_secret

    if not is_sys_admin and not is_valid_secret:
        return JSONResponse(
            status_code=403,
            content={
                "error": "🔒 ACCESS DENIED: Public emergency reset is disabled for security. You must pass ?secret=YOUR_EMERGENCY_SECRET or be logged in as System Admin."
            }
        )
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
            ("hqadmin@effutulibrary.gov.gh", "hq_admin", "admin123", "GHA-000000002-2"),
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
                    failed_login_attempts=0,
                    locked_until=None,
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
                user.failed_login_attempts = 0
                user.locked_until = None
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

@router.get("/forgot-password", response_class=HTMLResponse)
@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Forgot Password - Effutu Library</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <i class="fa-solid fa-key text-4xl text-amber-500 mb-2"></i>
                <h2 class="text-2xl font-extrabold text-slate-800">Reset Your Password</h2>
                <p class="text-xs text-slate-500">Enter your registered email to receive a password reset link.</p>
            </div>

            <form id="forgot-form" method="post" action="/api/auth/forgot-password" class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input type="email" name="email" id="email" required placeholder="your.email@gmail.com" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Send Reset Link
                </button>
            </form>
            <div id="forgot-alert" class="hidden p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-lg text-xs text-center font-semibold"></div>
            
            <div class="text-center pt-2 border-t border-slate-100">
                <a href="/auth/login" class="text-xs text-emerald-700 hover:underline font-semibold">Back to Sign In</a>
            </div>
        </div>

        <script>
        document.getElementById('forgot-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            const alertDiv = document.getElementById('forgot-alert');
            const email = document.getElementById('email').value;
            alertDiv.classList.remove('hidden');
            alertDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Processing request...';
            try {
                const res = await fetch('/api/auth/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                const data = await res.json();
                alertDiv.innerHTML = `
                    <div class="p-3 text-center space-y-1">
                        <i class="fa-solid fa-envelope-circle-check text-2xl text-emerald-600 mb-1 block"></i>
                        <p class="text-xs font-bold text-slate-800">Check Your Inbox</p>
                        <p class="text-[11px] text-slate-600 font-medium">${data.message || 'A secure password reset link has been sent to your registered email address. Please check your inbox.'}</p>
                    </div>
                `;
            } catch(ex) {
                alertDiv.innerHTML = `
                    <div class="p-3 text-center space-y-1">
                        <i class="fa-solid fa-envelope-circle-check text-2xl text-emerald-600 mb-1 block"></i>
                        <p class="text-xs font-bold text-slate-800">Check Your Inbox</p>
                        <p class="text-[11px] text-slate-600 font-medium">A secure password reset link has been sent to your registered email address. Please check your inbox.</p>
                    </div>
                `;
            }
        });
        </script>
    </body>
    </html>
    """)

@router.post("/api/auth/forgot-password")
@router.post("/auth/forgot-password")
async def forgot_password_api(
    request: Request,
    db: Session = Depends(get_db)
):
    from app.models import PasswordReset
    import secrets
    email = None
    try:
        body = await request.json()
        email = body.get("email")
    except Exception:
        try:
            form = await request.form()
            email = form.get("email")
        except Exception:
            pass

    if not email:
        return JSONResponse(status_code=400, content={"error": "Email address is required."})

    email_clean = email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if user:
        token = secrets.token_hex(16)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        
        pr = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
            used=False
        )
        db.add(pr)
        db.commit()

        frontend_url = os.getenv("FRONTEND_URL", str(request.base_url).rstrip('/'))
        reset_link = f"{frontend_url}/reset-password?token={token}"

        email_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h2 style="color: #047857;">Password Reset Request</h2>
            <p>Akwaaba <b>{user.full_name}</b>,</p>
            <p>We received a request to reset the password for your Effutu Municipal Library Network account.</p>
            <p style="margin: 20px 0;">
                <a href='{reset_link}' style='display:inline-block; padding:12px 24px; background-color:#047857; color:#ffffff; font-weight:bold; text-decoration:none; border-radius:8px;'>Reset Password Now</a>
            </p>
            <p style="font-size: 12px; color: #64748b;">Or copy this link into your browser:<br><code style="background: #f1f5f9; padding: 4px; font-size: 11px;">{reset_link}</code></p>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 15px;"><b>Note:</b> This secure link expires in 15 minutes. If you did not request a password reset, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #64748b;">Effutu Municipal Library Network</p>
        </div>
        """

        send_email(user.email, "Reset Your Password - Effutu Library Network", email_html)

    return JSONResponse(content={"message": "If an account is registered with this email, a secure password reset link has been sent to your inbox. Please check your email."})

@router.get("/reset-password", response_class=HTMLResponse)
@router.get("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_page(token: str = ""):
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Set New Password - Effutu Library</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <div class="text-center">
                <i class="fa-solid fa-lock text-4xl text-emerald-600 mb-2"></i>
                <h2 class="text-2xl font-extrabold text-slate-800">Set New Password</h2>
                <p class="text-xs text-slate-500">Create a secure new password for your account</p>
            </div>

            <div id="reset-alert" class="hidden p-3 rounded-lg text-xs text-center font-semibold"></div>

            <form id="reset-form" method="post" action="/api/auth/reset-password" class="space-y-4">
                <input type="hidden" name="token" id="token" value="{token}">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">New Password *</label>
                    <input type="password" name="new_password" id="new_password" required placeholder="••••••••" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Confirm New Password *</label>
                    <input type="password" id="confirm_password" required placeholder="••••••••" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Reset Password
                </button>
            </form>
        </div>

        <script>
        document.getElementById('reset-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            const alertDiv = document.getElementById('reset-alert');
            const token = document.getElementById('token').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;

            if (newPassword !== confirmPassword) {{
                alertDiv.className = 'p-3 rounded-lg text-xs text-center font-semibold bg-rose-50 border border-rose-300 text-rose-700';
                alertDiv.textContent = 'Passwords do not match!';
                alertDiv.classList.remove('hidden');
                return;
            }}

            try {{
                const res = await fetch('/api/auth/reset-password', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
                    body: JSON.stringify({{ token: token, newPassword: newPassword, new_password: newPassword }})
                }});

                const data = await res.json();
                if (res.ok) {{
                    alertDiv.className = 'p-3 rounded-lg text-xs text-center font-semibold bg-emerald-50 border border-emerald-300 text-emerald-800';
                    alertDiv.textContent = 'Password reset successful! Redirecting to Sign In...';
                    alertDiv.classList.remove('hidden');
                    setTimeout(() => {{ window.location.href = '/auth/login?msg=password_reset_success'; }}, 2000);
                }} else {{
                    alertDiv.className = 'p-3 rounded-lg text-xs text-center font-semibold bg-rose-50 border border-rose-300 text-rose-700';
                    alertDiv.textContent = data.error || 'Password reset failed or token expired.';
                    alertDiv.classList.remove('hidden');
                }}
            }} catch(ex) {{
                alertDiv.className = 'p-3 rounded-lg text-xs text-center font-semibold bg-rose-50 border border-rose-300 text-rose-700';
                alertDiv.textContent = 'An error occurred. Token may be invalid or expired.';
                alertDiv.classList.remove('hidden');
            }}
        }});
        </script>
    </body>
    </html>
    """)

@router.post("/api/auth/reset-password")
@router.post("/auth/reset-password")
async def reset_password_api(
    request: Request,
    db: Session = Depends(get_db)
):
    from app.models import PasswordReset
    token = None
    new_password = None

    try:
        body = await request.json()
        token = body.get("token")
        new_password = body.get("newPassword") or body.get("new_password")
    except Exception:
        try:
            form = await request.form()
            token = form.get("token")
            new_password = form.get("new_password") or form.get("newPassword")
        except Exception:
            pass

    if not token or not new_password:
        return JSONResponse(status_code=400, content={"error": "Token and new password are required."})

    now = datetime.datetime.utcnow()
    pr = db.query(PasswordReset).filter(
        PasswordReset.token == token.strip(),
        PasswordReset.used == False,
        PasswordReset.expires_at > now
    ).first()

    if not pr:
        return JSONResponse(status_code=400, content={"error": "Invalid, used, or expired reset token. Please request a new password reset link."})

    user = db.query(User).filter(User.id == pr.user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found."})

    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False
    pr.used = True
    db.commit()

    if user.email:
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h2 style="color: #047857;">Security Notice: Password Reset Completed</h2>
            <p>Akwaaba <b>{user.full_name}</b>,</p>
            <p>This email confirms that the password for your Effutu Municipal Library Network account was updated successfully.</p>
            <div style="background-color: #ecfdf5; padding: 12px; border-left: 4px solid #10b981; margin: 15px 0;">
                <b>Member ID:</b> {user.member_id or user.email}<br>
                <b>Security Status:</b> Password Reset Completed
            </div>
            <p style="font-size: 12px; color: #b91c1c; font-weight: bold;">If you did NOT perform this password change, please contact your branch librarian immediately to secure your account.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #64748b;">Effutu Municipal Library Network</p>
        </div>
        """
        send_email(user.email, "🔒 Security Alert: Your Password Was Changed - Effutu Library", email_body)

    return JSONResponse(content={"message": "Password updated successfully!"})



