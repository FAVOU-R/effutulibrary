from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.controllers.auth_controller import get_current_user, get_password_hash, send_email
import random, re

router = APIRouter(prefix="/librarian", tags=["Librarian"])

def require_librarian(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["librarian", "sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Only Librarians and Administrators can access this endpoint")
    return current_user

@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    q: str = "",
    v_filter: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    query = db.query(User)
    if current_user.role == "librarian":
        query = query.filter(User.branch_id == current_user.branch_id)
    
    if q.strip():
        search_term = f"%{q.strip().lower()}%"
        query = query.filter(
            (User.full_name.ilike(search_term)) |
            (User.phone.ilike(search_term)) |
            (User.id_number.ilike(search_term)) |
            (User.ghana_card_number.ilike(search_term)) |
            (User.member_id.ilike(search_term))
        )
    
    if v_filter == "pending":
        query = query.filter((User.verification_status == "pending") | (User.is_physically_verified == False))
    elif v_filter == "verified":
        query = query.filter((User.verification_status == "verified") & (User.is_physically_verified == True))
    elif v_filter == "rejected":
        query = query.filter(User.verification_status == "rejected")

    users = query.order_by(User.id.desc()).all()
    rows = ""
    for u in users:
        active_btn_color = "bg-rose-600 hover:bg-rose-700" if u.is_active else "bg-emerald-600 hover:bg-emerald-700"
        active_btn_label = "Deactivate" if u.is_active else "Activate"
        status_badge = "<span class='px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 rounded'>Active</span>" if u.is_active else "<span class='px-2 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 rounded'>DEACTIVATED</span>"

        sub_items = []
        if u.sex and u.sex != '-': 
            sub_items.append(u.sex)
        if u.school_occupation and u.school_occupation.strip():
            sub_items.append(u.school_occupation.strip())
        elif u.role and u.role != "patron":
            sub_items.append(u.role.replace('_', ' ').title())

        sub_text = " • ".join(sub_items) if sub_items else "Patron"

        id_disp = u.ghana_card_number or u.id_number or u.alt_contact or '-'
        id_type_label = (u.id_type or 'ghanacard').upper().replace('_', ' ')

        if u.verification_status == "pending" or not u.is_physically_verified:
            v_badge = "<span class='px-2 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-800 rounded'>⏳ Pending</span>"
        elif u.verification_status == "rejected":
            v_badge = f"<span class='px-2 py-0.5 text-[10px] font-bold bg-rose-100 text-rose-800 rounded' title='{u.rejection_reason or ''}'>❌ Rejected</span>"
        else:
            v_badge = "<span class='px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 rounded'>✅ Verified</span>"

        photo_link = f"<a href='{u.id_photo_url}' target='_blank' class='text-blue-600 font-bold hover:underline text-[11px]'><i class='fa-solid fa-image'></i> View Photo</a>" if u.id_photo_url else "<span class='text-slate-400'>No Photo</span>"
        branch_name = u.branch.name if u.branch else "Main Branch"

        contact_disp = u.email or u.phone or '-'
        loc_disp = u.location or branch_name

        rows += f"""
        <tr class='border-b border-slate-200 hover:bg-slate-50 transition text-xs'>
            <td class='p-3 font-mono font-bold text-emerald-800'>{u.member_id or f'ID-{u.id}'}</td>
            <td class='p-3 font-bold text-slate-800'>{u.full_name}<br><span class='text-[10px] text-slate-400 font-normal'>{sub_text}</span></td>
            <td class='p-3 font-mono text-slate-600'>{contact_disp}<br><span class='text-[10px] text-slate-400'>{loc_disp}</span></td>
            <td class='p-3 font-mono text-slate-600'><b>{id_type_label}:</b> {id_disp}<br>{photo_link}</td>
            <td class='p-3 uppercase font-bold text-slate-500'>{u.role.replace('_', ' ')}</td>
            <td class='p-3'>{status_badge}</td>
            <td class='p-3'>{v_badge}</td>
            <td class='p-3 space-x-1 whitespace-nowrap'>
                <form method="post" action="/librarian/users/{u.id}/toggle-active" class='inline'>
                    <button class='px-2 py-1 text-white font-bold rounded text-[11px] {active_btn_color}'>{active_btn_label}</button>
                </form>
                {'<form method="post" action="/librarian/users/' + str(u.id) + '/verify" class="inline"><button class="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded text-[11px]">Verify</button></form>' if (u.verification_status != 'verified') else ''}
                {'<button onclick="openRejectModal(' + str(u.id) + ')" class="px-2 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded text-[11px] inline">Reject</button>' if (u.verification_status != 'rejected') else ''}
                <form method="post" action="/librarian/users/{u.id}/reset-pwd" class='inline' title="Reset & Email Password">
                    <button class='px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded text-[11px]'><i class='fa-solid fa-key'></i> Reset Pwd</button>
                </form>
                <form method="post" action="/librarian/users/{u.id}/reset-pwd?mode=in_person" class='inline' title="In-Person Desk Reset (Show Temp Pwd)">
                    <button class='px-2 py-1 bg-slate-700 hover:bg-slate-800 text-white font-bold rounded text-[11px]'><i class='fa-solid fa-id-card'></i> Desk Reset</button>
                </form>
                <form method="post" action="/librarian/users/{u.id}/delete" onsubmit="return confirm('Delete this user account?');" class='inline'>
                    <button class='px-2 py-1 bg-slate-600 hover:bg-slate-700 text-white font-bold rounded text-[11px]'><i class='fa-solid fa-trash'></i></button>
                </form>
            </td>
        </tr>
        """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>Manage Users - Librarian Control Panel</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 class="text-2xl font-extrabold text-slate-800">User Management Desk</h2>
                    <p class="text-xs text-slate-500">Manage patron enrollments, ID verifications, account status, & credentials</p>
                </div>
                <div class="flex gap-2">
                    <a href="/librarian/users/add" class="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-lg shadow transition">
                        + Add User Manually
                    </a>
                    <a href="/dashboard/{current_user.role}" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition">
                        Back to Dashboard
                    </a>
                </div>
            </div>

            <!-- Filters & Search -->
            <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row justify-between items-center gap-4">
                <form method="get" action="/librarian/users" id="userSearchForm" class="flex flex-wrap items-center gap-3 w-full md:w-auto">
                    <div class="relative w-full sm:w-80">
                        <input type="search" id="userSearchInput" name="q" value="{q}" placeholder="Search name, phone, ID, email..." class="w-full pl-9 pr-8 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none shadow-sm">
                        <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-slate-400 text-xs"></i>
                    </div>
                    
                    <select name="v_filter" onchange="this.form.submit()" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-white font-bold text-slate-700 shadow-sm cursor-pointer">
                        <option value="all" {'selected' if v_filter == 'all' else ''}>All Verifications</option>
                        <option value="pending" {'selected' if v_filter == 'pending' else ''}>⏳ Pending (Yellow)</option>
                        <option value="verified" {'selected' if v_filter == 'verified' else ''}>✅ Verified (Green)</option>
                        <option value="rejected" {'selected' if v_filter == 'rejected' else ''}>❌ Rejected (Red)</option>
                    </select>

                    <button type="submit" class="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-lg shadow-sm transition">Filter</button>
                    {f'<a href="/librarian/users" class="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition">Clear Filter</a>' if q or v_filter != 'all' else ''}
                </form>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs paginated-table">
                        <thead class="bg-slate-100 uppercase text-slate-500 font-bold border-b border-slate-200">
                            <tr>
                                <th class="p-3">Member ID</th>
                                <th class="p-3">Full Name / Details</th>
                                <th class="p-3">Contact / Location</th>
                                <th class="p-3">ID Type / Photo</th>
                                <th class="p-3">Role</th>
                                <th class="p-3">Status</th>
                                <th class="p-3">Verification</th>
                                <th class="p-3">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else "<tr><td colspan='8' class='p-8 text-center text-slate-400 no-paginate'>No users found matching your search.</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Reject Modal -->
        <div id="rejectModal" class="hidden fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div class="bg-white rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
                <h3 class="text-lg font-bold text-slate-800">Reject User Verification</h3>
                <form id="rejectForm" method="post" action="" class="space-y-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Rejection Reason *</label>
                        <textarea name="reason" required placeholder="e.g. ID photo unclear / Invalid ID number" class="w-full p-2 border border-slate-300 rounded text-xs h-24 focus:ring-2 focus:ring-rose-500"></textarea>
                    </div>
                    <div class="flex justify-end gap-2">
                        <button type="button" onclick="closeRejectModal()" class="px-3 py-1.5 bg-slate-200 text-slate-700 font-bold text-xs rounded">Cancel</button>
                        <button type="submit" class="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded">Confirm Rejection</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
        function openRejectModal(userId) {{
            document.getElementById('rejectForm').action = '/librarian/users/' + userId + '/reject';
            document.getElementById('rejectModal').classList.remove('hidden');
        }}
        function closeRejectModal() {{
            document.getElementById('rejectModal').classList.add('hidden');
        }}

        // Responsive Paginator & Live Search Helper
        document.addEventListener('DOMContentLoaded', function() {{
            const tableEl = document.querySelector('table.paginated-table');
            if (!tableEl) return;
            const tbody = tableEl.querySelector('tbody');
            if (!tbody) return;

            const allRows = Array.from(tbody.querySelectorAll('tr')).filter(tr => !tr.classList.contains('no-paginate'));
            let activeRows = [...allRows];
            if (allRows.length === 0) return;

            let currentPage = 1;
            let pageSize = 10; // Default 10 records per page

            const headerBar = document.createElement('div');
            headerBar.className = "flex flex-col sm:flex-row justify-between items-center gap-3 p-3 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600 rounded-t-xl";
            
            headerBar.innerHTML = `
                <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-700">Show</span>
                    <select class="page-size-select bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-bold text-emerald-800 focus:outline-none focus:border-emerald-600 shadow-sm cursor-pointer">
                        <option value="5">5</option>
                        <option value="10" selected>10</option>
                        <option value="20">20</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="all">All</option>
                    </select>
                    <span class="text-slate-600">entries per page</span>
                </div>
                <div class="page-info-text text-slate-500 font-mono text-[11px]">
                    Showing <span class="start-idx font-bold text-slate-800">1</span> to <span class="end-idx font-bold text-slate-800">10</span> of <span class="total-idx font-bold text-slate-800">${{activeRows.length}}</span> entries
                </div>
                <div class="pagination-controls flex items-center gap-1">
                    <button type="button" class="btn-prev px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-100 rounded-lg text-slate-700 font-bold disabled:opacity-40 disabled:cursor-not-allowed transition">
                        <i class="fa-solid fa-chevron-left"></i> Prev
                    </button>
                    <span class="page-num-display px-3 py-1 font-mono font-bold text-slate-800 bg-white border border-slate-200 rounded-lg">1</span>
                    <button type="button" class="btn-next px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-100 rounded-lg text-slate-700 font-bold disabled:opacity-40 disabled:cursor-not-allowed transition">
                        Next <i class="fa-solid fa-chevron-right"></i>
                    </button>
                </div>
            `;

            tableEl.parentNode.insertBefore(headerBar, tableEl);

            function renderPage() {{
                let actualSize = (pageSize === 'all') ? activeRows.length : parseInt(pageSize);
                let totalPages = Math.ceil(activeRows.length / actualSize) || 1;
                if (currentPage > totalPages) currentPage = totalPages;
                if (currentPage < 1) currentPage = 1;

                let start = (currentPage - 1) * actualSize;
                let end = (pageSize === 'all') ? activeRows.length : Math.min(start + actualSize, activeRows.length);

                allRows.forEach(row => {{
                    row.style.display = 'none';
                }});

                activeRows.forEach((row, idx) => {{
                    if (idx >= start && idx < end) {{
                        row.style.display = '';
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});

                headerBar.querySelector('.start-idx').textContent = activeRows.length > 0 ? (start + 1) : 0;
                headerBar.querySelector('.end-idx').textContent = end;
                headerBar.querySelector('.total-idx').textContent = activeRows.length;
                headerBar.querySelector('.page-num-display').textContent = `${{currentPage}} / ${{totalPages}}`;

                headerBar.querySelector('.btn-prev').disabled = (currentPage === 1);
                headerBar.querySelector('.btn-next').disabled = (currentPage === totalPages || totalPages === 0);
            }}

            // Instant Live Search + Reset to Page 1 on Change or Clear
            const searchInput = document.getElementById('userSearchInput');
            if (searchInput) {{
                searchInput.addEventListener('input', function() {{
                    const term = this.value.toLowerCase().trim();
                    activeRows = allRows.filter(row => {{
                        const text = row.innerText.toLowerCase();
                        return !term || text.includes(term);
                    }});
                    currentPage = 1; // Always reset to first page when search changes or is cleared
                    renderPage();
                }});
                
                // Clear button event listener
                searchInput.addEventListener('search', function() {{
                    activeRows = [...allRows];
                    currentPage = 1;
                    renderPage();
                }});
            }}

            headerBar.querySelector('.page-size-select').addEventListener('change', (e) => {{
                pageSize = e.target.value === 'all' ? 'all' : parseInt(e.target.value);
                currentPage = 1;
                renderPage();
            }});

            headerBar.querySelector('.btn-prev').addEventListener('click', () => {{
                if (currentPage > 1) {{
                    currentPage--;
                    renderPage();
                }}
            }});

            headerBar.querySelector('.btn-next').addEventListener('click', () => {{
                let actualSize = (pageSize === 'all') ? activeRows.length : parseInt(pageSize);
                let totalPages = Math.ceil(activeRows.length / actualSize);
                if (currentPage < totalPages) {{
                    currentPage++;
                    renderPage();
                }}
            }});

            renderPage();
        }});
        </script>
    </body>
    </html>
    """)

@router.get("/users/add", response_class=HTMLResponse)
async def add_user_page(current_user: User = Depends(require_librarian)):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Manually Add User - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl shadow-lg p-6 space-y-4">
            <h2 class="text-2xl font-extrabold text-slate-800 text-center">Manually Enroll User</h2>
            <form method="post" action="/librarian/users/add" class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Full Name</label>
                    <input name="full_name" placeholder="Full Name" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Email Address</label>
                    <input name="email" type="email" placeholder="Email" required class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Ghana Card (Optional)</label>
                    <input name="ghana_card_number" placeholder="GHA-123456789-1" pattern="GHA-[0-9]{9}-[0-9]{1}" class="w-full text-sm font-mono border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none uppercase">
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Role</label>
                    <select name="role" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                        <option value="patron">Patron</option>
                        <option value="librarian">Librarian</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Branch ID</label>
                    <input name="branch_id" type="number" value="1" class="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:border-emerald-600 focus:outline-none">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow transition">
                    Enroll User & Send Email
                </button>
            </form>
            <div class="text-center pt-2">
                <a href="/librarian/users" class="text-xs text-slate-600 hover:underline">← Back to User List</a>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/users/add", response_class=HTMLResponse)
async def add_user_post(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    ghana_card_number: str = Form(""),
    role: str = Form("patron"),
    branch_id: int = Form(1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    email_clean = email.lower().strip()
    if db.query(User).filter(User.email == email_clean).first():
        return HTMLResponse("<h3>Email already exists</h3><a href='/librarian/users/add'>Back</a>", status_code=400)

    card_clean = ghana_card_number.upper().strip() if ghana_card_number else None
    if card_clean:
        if not re.match(r'^GHA-\d{9}-\d{1}$', card_clean):
            return HTMLResponse("<h3>Invalid Ghana Card format</h3><a href='/librarian/users/add'>Back</a>", status_code=400)
        if db.query(User).filter(User.ghana_card_number == card_clean).first():
            return HTMLResponse("<h3>Ghana Card already registered</h3><a href='/librarian/users/add'>Back</a>", status_code=400)

    default_pwd = f"Effutu@{random.randint(1000, 9999)}"
    member_num = random.randint(1000, 9999)
    prefix = "LIB" if role == "librarian" else "MBR"
    member_id = f"EFF-{prefix}-{member_num}"

    user = User(
        full_name=full_name.strip(),
        email=email_clean,
        ghana_card_number=card_clean,
        member_id=member_id,
        hashed_password=get_password_hash(default_pwd),
        role=role,
        branch_id=branch_id,
        is_approved=True,
        is_active=True,
        must_change_password=True,
        is_physically_verified=False
    )
    db.add(user)
    db.commit()

    base_url = str(request.base_url).rstrip('/')
    body = f"""
    <html><body style='font-family:Arial, sans-serif; color:#1e293b;'>
    <div style='max-width:500px; margin:0 auto; border:1px solid #cbd5e1; padding:20px; border-radius:8px;'>
        <h3 style='color:#15803d;'>Effutu Municipal Library</h3>
        <p>Dear <b>{full_name}</b>,</p>
        <p>Your library account has been manually created by your branch librarian.</p>
        <p><b>Member ID:</b> {member_id}<br>
        <b>Login Email:</b> {email_clean}<br>
        <b>Default Password:</b> <code>{default_pwd}</code><br>
        <b>Login URL:</b> <a href='{base_url}/auth/login'>{base_url}/auth/login</a></p>
        <p>Please change your password upon first login and present your physical Ghana Card during your first library visit.</p>
    </div>
    </body></html>
    """
    send_email(email_clean, "Effutu Library - Account Created by Librarian", body)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-xl p-6 text-center space-y-4 shadow-lg">
            <h3 class="text-xl font-bold text-emerald-700">User Successfully Added!</h3>
            <p class="text-xs text-slate-600">Default Password: <span class="bg-emerald-100 font-mono font-bold px-2 py-1 rounded text-emerald-900">{default_pwd}</span></p>
            <p class="text-xs text-slate-500">Credentials have been dispatched to <b>{email_clean}</b>.</p>
            <a href="/librarian/users" class="inline-block py-2 px-4 bg-emerald-700 text-white font-bold rounded text-xs">Back to Users Directory</a>
        </div>
    </body>
    </html>
    """)

@router.post("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return HTMLResponse("<h3>User not found</h3>", status_code=404)
    
    u.is_active = not u.is_active
    db.commit()
    return RedirectResponse(url="/librarian/users", status_code=303)

@router.post("/users/{user_id}/verify")
async def verify_physical(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    from app.models import UserPoint, Notification
    import datetime
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return HTMLResponse("<h3>User not found</h3>", status_code=404)

    u.is_physically_verified = True
    u.verification_status = "verified"
    u.is_approved = True
    u.is_active = True
    u.verified_by = current_user.id
    u.verified_at = datetime.datetime.utcnow()

    # Award +10 verification points
    point_entry = UserPoint(user_id=u.id, points=10, reason="Account ID Verification Bonus")
    db.add(point_entry)

    # Create notification
    notif = Notification(
        user_id=u.id,
        title="Account Verified! 🎉",
        message="Your library account is now fully verified. You can borrow up to 3 books at any branch.",
        type="success"
    )
    db.add(notif)
    db.commit()

    # Dispatch Verification Email
    try:
        branch_name = u.branch.name if u.branch else "Effutu Municipal Library"
        if u.email:
            send_email(
                u.email,
                f"✅ Account Verified - Effutu Library",
                f"<h3>Akwaaba {u.full_name}!</h3><p>✅ Verified! You can now borrow 3 books at {branch_name}.</p><p>You have also earned <b>+10 Reading Points</b>!</p>"
            )
    except Exception as ex:
        print(f"[VERIFY EMAIL DISPATCH WARNING] {ex}")

    return RedirectResponse(url="/librarian/users", status_code=303)

@router.post("/users/{user_id}/reject")
@router.get("/users/{user_id}/reject")
@router.post("/librarian/users/{user_id}/reject")
@router.get("/librarian/users/{user_id}/reject")
async def reject_user_verification(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    from app.models import Notification
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return HTMLResponse("<h3>User not found</h3>", status_code=404)

    reason = "ID Verification Failed"
    try:
        form = await request.form()
        reason = form.get("reason") or form.get("rejection_reason") or reason
    except Exception:
        try:
            data = await request.json()
            reason = data.get("reason") or data.get("rejection_reason") or reason
        except Exception:
            pass

    u.verification_status = "rejected"
    u.is_physically_verified = False
    u.rejection_reason = reason
    db.commit()

    try:
        notif = Notification(
            user_id=u.id,
            title="Verification Update ⚠️",
            message=f"Your account verification was declined. Reason: {reason}",
            type="warning"
        )
        db.add(notif)
        db.commit()
    except Exception as ex:
        print(f"[REJECT NOTIF WARNING] {ex}")

    try:
        if u.email:
            send_email(
                u.email,
                "Verification Update - Effutu Library",
                f"<p>Dear {u.full_name},</p><p>Your library account verification was declined.</p><p><b>Reason:</b> {reason}</p><p>Please visit your branch desk with your valid ID for assistance.</p>"
            )
    except Exception as ex:
        print(f"[REJECT USER EMAIL WARNING] {ex}")

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={"message": "User verification rejected", "reason": reason})

    return RedirectResponse(url="/librarian/users", status_code=303)

@router.post("/users/{user_id}/delete")
@router.get("/users/{user_id}/delete")
@router.delete("/users/{user_id}/delete")
@router.post("/librarian/users/{user_id}/delete")
@router.get("/librarian/users/{user_id}/delete")
@router.delete("/librarian/users/{user_id}/delete")
async def delete_user_account(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    from app.models import Reservation, UserPoint, PasswordReset, Notification, AILog
    
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=404, content={"error": "User not found"})
        return HTMLResponse("<h3>User not found</h3>", status_code=404)

    if u.role == "sys_admin" and current_user.role != "sys_admin":
        raise HTTPException(status_code=403, detail="Cannot delete System Administrator account")

    try:
        db.query(Reservation).filter(Reservation.user_id == user_id).delete(synchronize_session=False)
        db.query(UserPoint).filter(UserPoint.user_id == user_id).delete(synchronize_session=False)
        db.query(PasswordReset).filter(PasswordReset.user_id == user_id).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
        db.query(AILog).filter(AILog.user_id == user_id).delete(synchronize_session=False)

        db.delete(u)
        db.commit()
    except Exception as ex:
        db.rollback()
        print(f"[USER DELETE ERROR] {ex}")
        try:
            u.is_active = False
            u.verification_status = "rejected"
            db.commit()
        except Exception:
            pass

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={"message": "User deleted successfully"})

    return RedirectResponse(url="/librarian/users", status_code=303)

@router.post("/users/{user_id}/reset-pwd")
@router.get("/users/{user_id}/reset-pwd")
async def reset_pwd(
    request: Request,
    user_id: int,
    mode: str = "auto",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=404, content={"error": "User not found"})
        return HTMLResponse("<h3>User not found</h3>", status_code=404)

    try:
        q_mode = request.query_params.get("mode")
        if q_mode:
            mode = q_mode
    except Exception:
        pass

    has_email = bool(u.email and "@" in u.email)
    show_in_person = (mode == "in_person") or (not has_email)

    temp_pwd = f"Effutu@{random.randint(1000, 9999)}"
    u.hashed_password = get_password_hash(temp_pwd)
    u.must_change_password = True
    db.commit()

    base_url = str(request.base_url).rstrip('/')
    if has_email:
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h2 style="color: #047857;">Password Reset Notice</h2>
            <p>Akwaaba <b>{u.full_name}</b>,</p>
            <p>Your library account password has been reset by your branch librarian.</p>
            <p><b>Temporary Password:</b> <code style="background-color: #f1f5f9; padding: 6px 12px; font-size: 16px; font-weight: bold; border-radius: 6px;">{temp_pwd}</code></p>
            <div style="background-color: #fef3c7; padding: 12px; border-left: 4px solid #f59e0b; margin: 15px 0;">
                <b>Mandatory Action:</b> You will be required to create a new custom password immediately upon your next sign in.
            </div>
            <p><a href="{base_url}/auth/login" style="display: inline-block; padding: 10px 20px; background-color: #047857; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Sign In to Effutu Library</a></p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #64748b;">Effutu Municipal Library Network</p>
        </div>
        """
        send_email(u.email, "Effutu Library - Temporary Password Dispatched", body)

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={
            "message": f"Password reset successfully. Temp password: {temp_pwd if show_in_person else 'dispatched to email'}",
            "temp_password": temp_pwd if show_in_person else None,
            "must_change_password": True
        })

    in_person_block = f"""
    <div class="p-4 bg-amber-50 border border-amber-300 rounded-xl space-y-2 text-center">
        <p class="text-xs font-bold text-amber-900 uppercase tracking-wider"><i class="fa-solid fa-id-card text-amber-600 mr-1"></i> In-Person Physical Desk Temporary Password</p>
        <div class="text-2xl font-mono font-black text-amber-950 tracking-widest bg-white py-2.5 px-4 rounded-lg border border-amber-200 inline-block shadow-sm">
            {temp_pwd}
        </div>
        <p class="text-[11px] text-amber-800 font-medium leading-relaxed">
            {'Patron has no registered email address. ' if not has_email else ''}Provide this temporary password directly to patron <b>{u.full_name}</b> at the desk. They will be forced to change it upon signing in.
        </p>
    </div>
    """ if show_in_person else f"""
    <p class="text-xs text-slate-600 leading-relaxed">
        A temporary password has been dispatched directly to <b class="text-emerald-800">{u.email}</b>.
    </p>
    """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>Password Reset Confirmation - Librarian Desk</title>
    </head>
    <body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
        <div class="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-6 text-center space-y-4 shadow-xl">
            <div class="inline-flex items-center justify-center w-12 h-12 bg-emerald-100 text-emerald-800 rounded-full mb-1">
                <i class="fa-solid fa-key text-xl"></i>
            </div>
            <h3 class="text-lg font-extrabold text-slate-800">Password Reset Completed</h3>
            
            {in_person_block}

            <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl text-left text-xs text-slate-700 space-y-1">
                <p class="font-bold text-emerald-800"><i class="fa-solid fa-user-shield"></i> Forced Password Change Active</p>
                <p class="text-[11px] text-slate-500 font-medium">Account requires a new custom password on first sign in after reset.</p>
            </div>

            <div class="flex gap-2 pt-2">
                {'<a href="/librarian/users/' + str(u.id) + '/reset-pwd?mode=in_person" class="flex-1 py-2 px-3 bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold rounded-xl text-xs border border-amber-300">Show Desk Temp Pwd</a>' if (has_email and not show_in_person) else ''}
                <a href="/librarian/users" class="flex-1 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl text-xs shadow transition">
                    Return to User Desk
                </a>
            </div>
        </div>
    </body>
    </html>
    """)
