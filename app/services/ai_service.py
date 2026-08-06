import os
import json
import datetime
from sqlalchemy.orm import Session
from app.models import Book, BookCopy, Transaction, User

def get_live_stats(db: Session):
    if not db:
        return {"total_books": "N/A", "available_books": "N/A", "overdue_count": "N/A"}
    try:
        total_books = db.query(Book).count()
        available_books = db.query(BookCopy).filter(BookCopy.status == "available").count()
        now = datetime.datetime.utcnow()
        overdue_count = db.query(Transaction).filter(
            Transaction.return_date.is_(None),
            Transaction.due_date < now
        ).count()
        return {
            "total_books": total_books,
            "available_books": available_books,
            "overdue_count": overdue_count
        }
    except Exception as e:
        print(f"Error fetching DB stats: {e}")
        return {"total_books": 0, "available_books": 0, "overdue_count": 0}

def search_books_db(db: Session, query: str):
    if not db or not query:
        return []
    q_clean = f"%{query.lower().strip()}%"
    books = db.query(Book).filter(
        (Book.title.ilike(q_clean)) | (Book.author.ilike(q_clean)) | (Book.category.ilike(q_clean))
    ).limit(5).all()
    
    res = []
    for b in books:
        avail = db.query(BookCopy).filter(BookCopy.book_id == b.id, BookCopy.status == "available").count()
        res.append({
            "title": b.title,
            "author": b.author,
            "category": b.category,
            "available_copies": avail
        })
    return res

def get_overdue_list_db(db: Session):
    if not db:
        return []
    now = datetime.datetime.utcnow()
    overdue_txs = db.query(Transaction).filter(
        Transaction.return_date.is_(None),
        Transaction.due_date < now
    ).limit(10).all()
    
    res = []
    for tx in overdue_txs:
        patron_name = tx.patron.full_name if tx.patron else "Unknown"
        book_title = tx.book_copy.book.title if (tx.book_copy and tx.book_copy.book) else "Unknown Book"
        res.append({
            "patron": patron_name,
            "book": book_title,
            "due_date": tx.due_date.strftime("%Y-%m-%d")
        })
    return res

def get_user_by_ghana_card_db(db: Session, card_number: str):
    if not db or not card_number:
        return None
    card_clean = card_number.upper().strip()
    user = db.query(User).filter(User.ghana_card_number == card_clean).first()
    if user:
        return {
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
            "ghana_card": user.ghana_card_number,
            "approved": user.is_approved
        }
    return None

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "Search for books in the library catalog by title, author, or category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keyword"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_list",
            "description": "Get a list of patrons with currently overdue books.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_by_ghana_card",
            "description": "Look up a user account by their Ghana Card number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_number": {"type": "string", "description": "Ghana Card number e.g. GHA-123456789-1"}
                },
                "required": ["card_number"]
            }
        }
    }
]

def get_ai_response(message: str, db: Session = None) -> str:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return "GROQ_API_KEY not found in environment. Please set GROQ_API_KEY on Render."

    stats = get_live_stats(db)

    system_prompt = f"""
You ARE Effutu Library AI with LIVE database access!

LIVE STATS:
- Total books cataloged: {stats['total_books']}
- Available copies right now: {stats['available_books']}
- Currently overdue transactions: {stats['overdue_count']}

Key capabilities:
- You CAN check overdue books, recommend real books from the database, and verify users by Ghana Card (GHA-XXXXXXXXX-X).
- NEVER say you don't have access to the database — you DO! Use the provided tools/functions when asked for books, overdue lists, or member details.
- If a user asks about user accounts or librarian actions, remind them to visit /librarian/users or check their dashboard.
- Always be friendly, concise, professional, with a warm Ghanaian touch.
"""

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            max_tokens=500
        )

        response_message = response.choices[0].message
        tool_calls = getattr(response_message, "tool_calls", None)

        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")
                
                result = None
                if fn_name == "search_books":
                    result = search_books_db(db, args.get("query", ""))
                elif fn_name == "get_overdue_list":
                    result = get_overdue_list_db(db)
                elif fn_name == "get_user_by_ghana_card":
                    result = get_user_by_ghana_card_db(db, args.get("card_number", ""))
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result if result is not None else {"result": "None"})
                })

            second_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=500
            )
            return second_response.choices[0].message.content

        return response_message.content or "No response from AI."

    except ImportError:
        return "Groq package not installed. Please run `pip install groq`."
    except Exception as e:
        print(f"Groq AI error: {e}")
        return f"AI Assistant temporarily offline. Please contact librarian. Error: {str(e)[:150]}"
