from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
from app.database import get_db
from app.models import UserPoint, User, Branch
from app.controllers.auth_controller import get_current_user_optional, get_current_user

router = APIRouter(prefix="", tags=["Points & Leaderboard"])

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user_optional(request, db)

    # Calculate Top 10 readers by SUM(points) for current month
    now = datetime.datetime.utcnow()
    start_of_month = datetime.datetime(now.year, now.month, 1)

    top_readers_query = db.query(
        UserPoint.user_id,
        func.sum(UserPoint.points).label("total_points")
    ).filter(
        UserPoint.created_at >= start_of_month
    ).group_by(UserPoint.user_id).order_by(func.sum(UserPoint.points).desc()).limit(10).all()

    top_list = []
    for rank, (uid, pts) in enumerate(top_readers_query, start=1):
        u = db.query(User).filter(User.id == uid).first()
        if u:
            branch_name = u.branch.name if u.branch else "Effutu Municipal Library"
            top_list.append({
                "rank": rank,
                "name": u.full_name,
                "branch": branch_name,
                "school": u.school_occupation or "Patron",
                "points": pts
            })

    rows = ""
    for r in top_list:
        trophy = "🥇" if r["rank"] == 1 else ("🥈" if r["rank"] == 2 else ("🥉" if r["rank"] == 3 else f"#{r['rank']}"))
        rows += f"""
        <tr class='border-b border-slate-200 hover:bg-slate-50 transition text-xs'>
            <td class='p-3 text-lg font-bold'>{trophy}</td>
            <td class='p-3 font-bold text-slate-800'>{r['name']}</td>
            <td class='p-3 text-slate-600'>{r['school']}</td>
            <td class='p-3 text-slate-600'>{r['branch']}</td>
            <td class='p-3 font-mono font-bold text-emerald-700 text-sm'>+{r['points']} pts</td>
        </tr>
        """

    my_points = 0
    if current_user:
        my_pts_sum = db.query(func.sum(UserPoint.points)).filter(UserPoint.user_id == current_user.id).scalar()
        my_points = my_pts_sum or 0

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>Reading Competition Leaderboard - Effutu Municipal Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-4xl mx-auto space-y-6">
            <div class="bg-gradient-to-r from-emerald-800 to-teal-900 text-white rounded-xl p-6 shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 class="text-3xl font-extrabold flex items-center gap-2">
                        🏆 Top Readers This Month
                    </h2>
                    <p class="text-xs text-emerald-200 mt-1">Effutu Municipal Library Network Monthly Reading Champions</p>
                </div>
                <div class="bg-white/10 backdrop-blur-md px-4 py-2 rounded-lg border border-white/20 text-center">
                    <div class="text-[10px] uppercase font-bold text-emerald-200">My Total Points</div>
                    <div class="text-2xl font-black font-mono text-amber-300">+{my_points} pts</div>
                </div>
            </div>

            <!-- Point Rules Card -->
            <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-xs text-slate-600">
                <h4 class="font-bold text-slate-800 mb-2 uppercase tracking-wide"><i class="fa-solid fa-star text-amber-500"></i> How to Earn Reading Points:</h4>
                <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center font-bold">
                    <div class="p-2 bg-emerald-50 rounded border border-emerald-200 text-emerald-900">ID Verification<br><span class="text-sm font-mono">+10 pts</span></div>
                    <div class="p-2 bg-blue-50 rounded border border-blue-200 text-blue-900">Borrow Book<br><span class="text-sm font-mono">+5 pts</span></div>
                    <div class="p-2 bg-amber-50 rounded border border-amber-200 text-amber-900">Return On Time<br><span class="text-sm font-mono">+20 pts</span></div>
                    <div class="p-2 bg-purple-50 rounded border border-purple-200 text-purple-900">Reserve & Collect<br><span class="text-sm font-mono">+5 pts</span></div>
                    <div class="p-2 bg-rose-50 rounded border border-rose-200 text-rose-900">Overdue Fine<br><span class="text-sm font-mono">-10 pts</span></div>
                </div>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div class="p-4 bg-slate-50 border-b border-slate-200 font-bold text-slate-700 text-sm flex justify-between items-center">
                    <span>Monthly Reader Standings</span>
                    <a href="/catalog" class="text-xs text-emerald-700 font-bold hover:underline">Borrow Books & Earn Points →</a>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-100 uppercase text-slate-500 font-bold border-b border-slate-200">
                            <tr>
                                <th class="p-3">Rank</th>
                                <th class="p-3">Reader Name</th>
                                <th class="p-3">School / Occupation</th>
                                <th class="p-3">Branch Library</th>
                                <th class="p-3">Points Earned</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else "<tr><td colspan='5' class='p-8 text-center text-slate-400'>No points recorded this month yet. Start reading to lead!</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="text-center">
                <a href="/dashboard/patron" class="px-4 py-2 bg-slate-200 text-slate-700 font-bold text-xs rounded-lg hover:bg-slate-300 transition">Back to Patron Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """)

@router.get("/api/points/my")
async def get_my_points(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total = db.query(func.sum(UserPoint.points)).filter(UserPoint.user_id == current_user.id).scalar() or 0
    history = db.query(UserPoint).filter(UserPoint.user_id == current_user.id).order_by(UserPoint.id.desc()).all()
    return {
        "total_points": total,
        "history": [{
            "points": h.points,
            "reason": h.reason,
            "created_at": h.created_at.strftime("%Y-%m-%d %H:%M")
        } for h in history]
    }
