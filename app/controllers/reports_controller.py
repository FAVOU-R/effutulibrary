from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv, io, datetime
from app.database import get_db
from app.models import User, Branch, Book, Transaction, BookCopy
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="", tags=["GLA Reports & Analytics"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Only Admins & Librarians can view reports")
    return current_user

@router.get("/admin/reports", response_class=HTMLResponse)
async def gla_reports_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total_users = db.query(User).count()
    male_count = db.query(User).filter(User.sex == "Male").count()
    female_count = db.query(User).filter(User.sex == "Female").count()
    other_sex_count = total_users - (male_count + female_count)

    pending_verifications = db.query(User).filter((User.verification_status == "pending") | (User.is_physically_verified == False)).count()
    
    now = datetime.datetime.utcnow()
    start_of_month = datetime.datetime(now.year, now.month, 1)
    borrowed_this_month = db.query(Transaction).filter(Transaction.issue_date >= start_of_month).count()
    overdue_count = db.query(Transaction).filter(Transaction.return_date.is_(None), Transaction.due_date < now).count()

    # Branch Stats
    branches = db.query(Branch).all()
    branch_labels = []
    branch_user_counts = []
    for b in branches:
        branch_labels.append(b.name)
        cnt = db.query(User).filter(User.branch_id == b.id).count()
        branch_user_counts.append(cnt)

    # School Breakdown Table
    school_stats = db.query(
        User.school_occupation,
        func.count(User.id)
    ).group_by(User.school_occupation).order_by(func.count(User.id).desc()).limit(10).all()

    school_rows = ""
    for school_name, count in school_stats:
        school_label = school_name if school_name else "Not Specified / Community Patron"
        school_rows += f"""
        <tr class='border-b border-slate-200 text-xs'>
            <td class='p-2 font-bold text-slate-800'>{school_label}</td>
            <td class='p-2 font-mono font-bold text-emerald-700'>{count} patrons</td>
        </tr>
        """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>GLA Analytics & Municipal Reports - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            <!-- Header -->
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 class="text-2xl font-extrabold text-slate-800">Ghana Library Authority (GLA) Analytics</h2>
                    <p class="text-xs text-slate-500">Municipal patron enrollment, demographic breakdown, branch performance, & borrowing statistics</p>
                </div>
                <div class="flex gap-2">
                    <a href="/admin/reports/gla-export" class="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-lg shadow transition flex items-center gap-2">
                        <i class="fa-solid fa-file-excel text-sm"></i> 📊 Download GLA Report (Excel/CSV)
                    </a>
                    <a href="/dashboard/{current_user.role}" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition">
                        Back to Dashboard
                    </a>
                </div>
            </div>

            <!-- KPI Metric Cards -->
            <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                    <div class="text-[10px] font-bold uppercase text-slate-400">Total Registered Users</div>
                    <div class="text-2xl font-black text-slate-800 font-mono mt-1">{total_users}</div>
                </div>
                <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                    <div class="text-[10px] font-bold uppercase text-slate-400">Borrowed This Month</div>
                    <div class="text-2xl font-black text-emerald-700 font-mono mt-1">{borrowed_this_month}</div>
                </div>
                <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                    <div class="text-[10px] font-bold uppercase text-slate-400">Active Overdues</div>
                    <div class="text-2xl font-black text-rose-600 font-mono mt-1">{overdue_count}</div>
                </div>
                <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                    <div class="text-[10px] font-bold uppercase text-slate-400">Pending Verification</div>
                    <div class="text-2xl font-black text-amber-600 font-mono mt-1">{pending_verifications}</div>
                </div>
                <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                    <div class="text-[10px] font-bold uppercase text-slate-400">Active Municipal Branches</div>
                    <div class="text-2xl font-black text-blue-700 font-mono mt-1">{len(branches)}</div>
                </div>
            </div>

            <!-- Charts Section -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Sex Ratio Pie Chart -->
                <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                    <h3 class="font-bold text-slate-800 text-sm mb-4">Patron Demographics by Sex</h3>
                    <div class="h-64">
                        <canvas id="sexChart"></canvas>
                    </div>
                </div>

                <!-- Branch Distribution Bar Chart -->
                <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm lg:col-span-2">
                    <h3 class="font-bold text-slate-800 text-sm mb-4">Patron Registration by Library Branch</h3>
                    <div class="h-64">
                        <canvas id="branchChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- School / Institution Breakdown Table -->
            <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <h3 class="font-bold text-slate-800 text-sm mb-3">Top Enrolled Schools & Institutions</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-100 text-slate-500 font-bold uppercase text-[10px] border-b">
                                <th class="p-2">School / Occupation</th>
                                <th class="p-2">Total Enrolled Patrons</th>
                            </tr>
                        </thead>
                        <tbody>
                            {school_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
        // Sex Pie Chart
        const sexCtx = document.getElementById('sexChart').getContext('2d');
        new Chart(sexCtx, {{
            type: 'pie',
            data: {{
                labels: ['Male', 'Female', 'Other/Unspecified'],
                datasets: [{{
                    data: [{male_count}, {female_count}, {other_sex_count}],
                    backgroundColor: ['#2563eb', '#ec4899', '#94a3b8']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        // Branch Bar Chart
        const branchCtx = document.getElementById('branchChart').getContext('2d');
        new Chart(branchCtx, {{
            type: 'bar',
            data: {{
                labels: {branch_labels},
                datasets: [{{
                    label: 'Enrolled Patrons',
                    data: {branch_user_counts},
                    backgroundColor: '#059669'
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
        </script>
    </body>
    </html>
    """)

@router.get("/admin/reports/gla-export")
async def export_gla_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header
    writer.writerow(["=== EFFUTU MUNICIPAL LIBRARY NETWORK - GLA COMPLIANCE REPORT ==="])
    writer.writerow(["Report Date", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")])
    writer.writerow([])

    # 2. Users Sheet
    writer.writerow(["--- USER ENROLLMENT DIRECTORY ---"])
    writer.writerow(["Member ID", "Full Name", "Sex", "Phone", "Email", "Branch", "School/Occupation", "Location", "ID Type", "ID Number", "Verification Status"])
    
    users = db.query(User).all()
    for u in users:
        branch_name = u.branch.name if u.branch else "Main Branch"
        writer.writerow([
            u.member_id or f"ID-{u.id}",
            u.full_name,
            u.sex or "Unspecified",
            u.phone or "",
            u.email or "",
            branch_name,
            u.school_occupation or "",
            u.location or "",
            u.id_type or "",
            u.id_number or u.ghana_card_number or "",
            u.verification_status or "pending"
        ])
    writer.writerow([])

    # 3. Active Loans Sheet
    writer.writerow(["--- LOANS & TRANSACTIONS RECORD ---"])
    writer.writerow(["Transaction ID", "Patron Name", "Member ID", "Book Title", "Issue Date", "Due Date", "Status"])
    txs = db.query(Transaction).all()
    for t in txs:
        patron_name = t.patron.full_name if t.patron else "Unknown"
        patron_mid = t.patron.member_id if t.patron else "-"
        book_title = t.book_copy.book.title if (t.book_copy and t.book_copy.book) else "Unknown"
        writer.writerow([
            f"#TX-{t.id}",
            patron_name,
            patron_mid,
            book_title,
            t.issue_date.strftime("%Y-%m-%d") if t.issue_date else "-",
            t.due_date.strftime("%Y-%m-%d") if t.due_date else "-",
            t.status
        ])

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=GLA_Effutu_Library_Report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    return response
