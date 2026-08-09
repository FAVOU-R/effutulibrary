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
    if not db:
        return []
    q_str = (query or "").lower().strip()
    general_queries = ["all", "available", "books", "catalog", "list", "show", "what books", "recommend", "inventory", "do you have"]
    is_general = any(g in q_str for g in general_queries) or len(q_str) < 3

    if is_general or not q_str:
        books = db.query(Book).limit(8).all()
    else:
        q_clean = f"%{q_str}%"
        books = db.query(Book).filter(
            (Book.title.ilike(q_clean)) | (Book.author.ilike(q_clean)) | (Book.category.ilike(q_clean))
        ).limit(5).all()
        if not books:
            # Fallback to general list if specific search yielded no results
            books = db.query(Book).limit(6).all()

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

def get_overdue_list_db(db: Session, current_user: User = None):
    if not db:
        return {"error": "Database session unavailable."}
    
    if not current_user:
        return {"error": "🔒 Authentication required. Please log in at /login to view account details."}

    user_role = getattr(current_user, "role", "guest")
    now = datetime.datetime.utcnow()

    # Normal Patrons / Students: CAN ONLY VIEW THEIR OWN OVERDUE ITEMS
    if user_role in ["patron", "user"]:
        overdue_txs = db.query(Transaction).filter(
            Transaction.patron_id == current_user.id,
            Transaction.return_date.is_(None),
            Transaction.due_date < now
        ).all()
        
        user_items = []
        for tx in overdue_txs:
            book_title = tx.book_copy.book.title if (tx.book_copy and tx.book_copy.book) else "Unknown Book"
            user_items.append({
                "book_title": book_title,
                "due_date": tx.due_date.strftime("%Y-%m-%d"),
                "status": "OVERDUE"
            })

        return {
            "your_overdue_count": len(user_items),
            "your_overdue_books": user_items,
            "privacy_notice": "🔒 Ghana Data Protection Compliance: Patrons can only view their own personal loan records. Global overdue lists are restricted to Librarians."
        }

    # Librarians & Admins: Full system/branch access
    if user_role in ["librarian", "sys_admin", "hq_admin", "admin"]:
        overdue_txs = db.query(Transaction).filter(
            Transaction.return_date.is_(None),
            Transaction.due_date < now
        ).limit(15).all()
        
        res = []
        for tx in overdue_txs:
            patron_name = tx.patron.full_name if tx.patron else "Unknown"
            patron_phone = tx.patron.phone if tx.patron else "-"
            book_title = tx.book_copy.book.title if (tx.book_copy and tx.book_copy.book) else "Unknown Book"
            res.append({
                "patron_name": patron_name,
                "patron_phone": patron_phone,
                "book": book_title,
                "due_date": tx.due_date.strftime("%Y-%m-%d")
            })
        return {"total_overdue_count": len(res), "overdue_patrons": res}

    return {"error": "Unauthorized access."}

def get_user_by_ghana_card_db(db: Session, card_number: str, current_user: User = None):
    if not db:
        return {"error": "Database session unavailable."}

    if not current_user:
        return {"error": "🔒 Authentication required. Please log in at /login to access account details."}

    card_clean = card_number.upper().strip() if card_number else ""
    user_role = getattr(current_user, "role", "guest")

    # Normal Patrons / Students: STRICT SECURITY CHECK
    if user_role in ["patron", "user"]:
        own_card = (getattr(current_user, "ghana_card_number", "") or "").upper().strip()
        own_id_num = (getattr(current_user, "id_number", "") or "").upper().strip()

        # Check if searching for someone else's ID
        if card_clean and (card_clean != own_card and card_clean != own_id_num):
            return {
                "error": f"❌ SECURITY & PRIVACY BREACH PREVENTED: You can ONLY view your own account information. Your registered ID is {own_card or own_id_num or 'Not Registered'}. You cannot query other patrons' Ghana Cards."
            }

        # Return ONLY their own info
        active_txs = db.query(Transaction).filter(
            Transaction.patron_id == current_user.id,
            Transaction.return_date.is_(None)
        ).all()
        
        now = datetime.datetime.utcnow()
        loans = []
        for tx in active_txs:
            b_title = tx.book_copy.book.title if (tx.book_copy and tx.book_copy.book) else "Book"
            loans.append({
                "book": b_title,
                "due_date": tx.due_date.strftime("%Y-%m-%d"),
                "is_overdue": tx.due_date < now
            })

        return {
            "name": current_user.full_name,
            "member_id": current_user.member_id,
            "id_type": current_user.id_type,
            "verification_status": current_user.verification_status,
            "your_active_loans": loans
        }

    # Librarians & Admins: Full patron lookup allowed
    if user_role in ["librarian", "sys_admin", "hq_admin", "admin"]:
        user = db.query(User).filter(
            (User.ghana_card_number == card_clean) | (User.id_number == card_clean)
        ).first()
        if user:
            active_txs = db.query(Transaction).filter(
                Transaction.patron_id == user.id,
                Transaction.return_date.is_(None)
            ).all()
            return {
                "name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "ghana_card": user.ghana_card_number,
                "id_number": user.id_number,
                "id_type": user.id_type,
                "verification_status": user.verification_status,
                "active_loans_count": len(active_txs)
            }
        return {"error": f"No user account found matching ID: {card_clean}"}

    return {"error": "Unauthorized access."}

def web_search_online(query: str):
    """Perform live real-time internet search using Multi-Engine Fallback (DuckDuckGo Lite, Google News RSS, Wikipedia, DDG API)"""
    if not query:
        return [{"snippet": "Query cannot be empty"}]
    
    import re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    results = []

    # 1. Try DuckDuckGo Lite (Best for factual answers, current leaders, general knowledge, sports & news)
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        snippets = re.findall(r'result-snippet[^>]*>(.*?)</td>', html, re.DOTALL)
        for s in snippets[:4]:
            clean_text = re.sub(r'<[^>]+>', '', s).strip()
            if clean_text:
                results.append({"snippet": clean_text})
        if results:
            return results
    except Exception as e:
        print(f"DuckDuckGo Lite search warning: {e}")

    # 2. Try Google News RSS Feed (Best for breaking news, WASSCE timetables, current events)
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_content = resp.read()
            root = ET.fromstring(xml_content)
            items = root.findall('.//item')
            for item in items[:4]:
                title = item.find('title')
                pubDate = item.find('pubDate')
                t_text = title.text if title is not None else ""
                d_text = pubDate.text if pubDate is not None else ""
                if t_text:
                    results.append({"snippet": f"Headline: {t_text} (Published: {d_text})"})
            if results:
                return results
    except Exception as e:
        print(f"Google News RSS search warning: {e}")

    # 3. Try Wikipedia OpenSearch API
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=3&namespace=0&format=json"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            wiki_data = json.loads(resp.read().decode('utf-8'))
            if len(wiki_data) >= 3 and wiki_data[2]:
                for desc in wiki_data[2][:3]:
                    if desc:
                        results.append({"snippet": desc})
                if results:
                    return results
    except Exception as wiki_err:
        print(f"Wikipedia API search warning: {wiki_err}")

    # 4. Fallback to DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            abstract = data.get("AbstractText", "")
            if abstract:
                return [{"snippet": abstract}]
            related = data.get("RelatedTopics", [])
            for r in related[:3]:
                if isinstance(r, dict) and "Text" in r:
                    results.append({"snippet": r["Text"]})
            if results:
                return results
    except Exception as api_err:
        print(f"DDG Instant API warning: {api_err}")

    return [{"snippet": f"Live web search checked online for '{query}'. Please verify latest updates on the official WAEC Ghana portal (waecgh.org)."}]

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "Search for books in the public library catalog by title, author, or category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keyword e.g. WASSCE, Biology, Mathematics"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform live real-time internet web search for current events, WAEC/WASSCE latest news, educational updates, or general topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Web search query e.g. WASSCE 2026 timetable, Ghana education news"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_list",
            "description": "Get overdue books info. Checks current user role to restrict visibility per Ghana Data Protection Act.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Optional patron filter name"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_by_ghana_card",
            "description": "Look up account by Ghana Card or ID number. Restricted to user's own account for patrons; full lookup for librarians.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_number": {"type": "string", "description": "Ghana Card or ID number e.g. GHA-123456789-1"}
                },
                "required": ["card_number"]
            }
        }
    }
]

def get_user_reading_history(db: Session, current_user: User):
    if not db or not current_user:
        return {"recent_borrowed": [], "favorite_categories": [], "personalized_recommendations": []}
    try:
        txs = db.query(Transaction).filter(Transaction.patron_id == current_user.id).all()
        borrowed_book_ids = set()
        borrowed_titles = []
        categories_count = {}

        for tx in txs:
            if tx.book_copy and tx.book_copy.book:
                b = tx.book_copy.book
                borrowed_book_ids.add(b.id)
                borrowed_titles.append(b.title)
                cat = (b.category or "General").title()
                categories_count[cat] = categories_count.get(cat, 0) + 1

        fav_cats = sorted(categories_count.keys(), key=lambda c: categories_count[c], reverse=True)[:3]

        # Recommend available books in favorite categories that user hasn't borrowed yet
        recs = []
        if fav_cats:
            rec_books = db.query(Book).filter(
                Book.category.in_(fav_cats),
                ~Book.id.in_(borrowed_book_ids) if borrowed_book_ids else True
            ).limit(4).all()
            for rb in rec_books:
                recs.append({"title": rb.title, "author": rb.author, "category": rb.category})

        # Fallback to general books if user has no specific category matches
        if not recs:
            general_books = db.query(Book).filter(~Book.id.in_(borrowed_book_ids) if borrowed_book_ids else True).limit(4).all()
            for gb in general_books:
                recs.append({"title": gb.title, "author": gb.author, "category": gb.category})

        return {
            "recent_borrowed": borrowed_titles[-5:],
            "favorite_categories": fav_cats,
            "personalized_recommendations": recs
        }
    except Exception as e:
        print(f"Error fetching user reading history: {e}")
        return {"recent_borrowed": [], "favorite_categories": [], "personalized_recommendations": []}

def get_ai_response(message: str, db: Session = None, current_user: User = None) -> str:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return "Akwaaba! GROQ_API_KEY is not configured on Render environment. Please set GROQ_API_KEY to enable Araba AI."

    from datetime import datetime
    import re
    now_str = datetime.utcnow().strftime('%A, %B %d, %Y at %H:%M:%S UTC')

    stats = get_live_stats(db)
    user_role = getattr(current_user, "role", "guest") if current_user else "guest"
    full_name = getattr(current_user, "full_name", "") if current_user else ""
    first_name = full_name.strip().split()[0] if full_name.strip() else "Patron"

    # Fetch User's Live Reading History and Tailored Recommendations from DB
    user_history = get_user_reading_history(db, current_user)

    # 1. LOCAL MUNICIPAL LIBRARY DATABASE SEARCH (PRIMARY SOURCE)
    catalog_context = ""
    db_matches = []
    if db:
        try:
            db_matches = search_books_db(db, message)
            if db_matches:
                catalog_context = f"\nLIVE MUNICIPAL LIBRARY CATALOG MATCHES IN LOCAL DB FOR '{message}':\n" + json.dumps(db_matches, indent=2)
        except Exception as db_err:
            print(f"DB catalog search warning: {db_err}")

    # 2. REAL-TIME INTERNET WEB SEARCH (SECONDARY SOURCE FOR EXTERNAL WORLD QUESTIONS)
    realtime_keywords = [
        "president", "who is", "current", "latest", "news", "today", "now",
        "wassce", "bece", "waec", "timetable", "election", "weather", "sports",
        "governor", "prime minister", "minister", "champion", "winner", "leader"
    ]
    message_lower = message.lower()
    needs_web_search = any(k in message_lower for k in realtime_keywords)

    live_web_context = ""
    # Perform external web search only if requested or if query asks for non-catalog world information
    if needs_web_search:
        try:
            web_results = web_search_online(message)
            if web_results:
                snippets = [r.get('snippet', '') for r in web_results if r.get('snippet')]
                if snippets:
                    live_web_context = f"\nLIVE REAL-TIME INTERNET SEARCH RESULTS FOR '{message}':\n" + "\n".join([f"- {s}" for s in snippets])
        except Exception as err:
            print(f"Pre-query web search warning: {err}")

    system_prompt = f"""
You are Araba, the intelligent, friendly Ghanaian AI assistant for the Effutu Municipal Library Network.
Akwaaba is your standard Ghanaian greeting!

CURRENT SYSTEM DATE & TIME: {now_str}

GREETING RULE:
- ALWAYS address the user by their FIRST NAME ONLY (e.g. "Akwaaba, {first_name}!"). NEVER use their full name (do NOT say "Akwaaba, {full_name}").

DATA SOURCES & SEARCH PRIORITY:
1. LOCAL MUNICIPAL LIBRARY DATABASE (PRIMARY SOURCE - REAL-TIME LIVE DB SYNC):
{catalog_context or "   - No direct title/category match found in local catalog DB for this exact query term."}
   - RULE: ALWAYS check and prioritize local library database results above when patrons ask for books, study materials, or library inventory.

2. REAL-TIME INTERNET WEB SEARCH (SECONDARY / EXTERNAL SOURCE):
{live_web_context or "   - No external web search needed/performed."}
   - RULE: Use real-time web search results for questions about current world leaders (e.g. US President, Ghana President), breaking news, weather, or WAEC timetables.

USER READING HISTORY & PERSONALIZED RECOMMENDATIONS (LIVE FROM DB):
- Books previously borrowed by {first_name}: {user_history['recent_borrowed'] or 'No past loans recorded yet'}
- Favorite Reading Categories: {user_history['favorite_categories'] or 'General'}
- Tailored Book Recommendations for {first_name}: {json.dumps(user_history['personalized_recommendations'])}

RECOMMENDATION RULE:
- When {first_name} asks for book recommendations or browsing suggestions, suggest books based on their tailored recommendations and favorite reading categories listed above.

STRICT RESPONSE STYLE RULES:
1. REAL-TIME FACTUAL ACCURACY & ZERO OUTDATED HALLUCINATIONS:
   - YOUR PRE-TRAINED INTERNAL MEMORY IS OUTDATED regarding political leaders, government officials, sports, current events, and news.
   - ALWAYS extract the answer directly from the LIVE REAL-TIME INTERNET SEARCH RESULTS provided above.
   - If asked about the current US President, state clearly: "Donald Trump is the current President of the United States." NEVER state Joe Biden is President or invent health gossip.
2. BE DIRECT & CONCISE: Provide clear, direct, and authoritative answers in 1 to 3 sentences maximum.
3. ABSOLUTELY NO META-COMMENTARY: NEVER use phrases like "Based on the live real-time internet search results...", "It appears that...", "This is not explicitly confirmed...", "I would recommend checking latest news sources...", or dumping system timestamps.
4. NO UNCERTAIN HEDGING: State facts directly and confidently without waffling or disclaimers.
5. WARM & HELPFUL: Keep responses clean, sharp, and helpful with a friendly Ghanaian Akwaaba tone.

Active Session User: {first_name} (Full Name: {full_name or 'Guest'}, Role: {user_role})

LIVE CATALOG STATS:
- Total books cataloged in DB: {stats['total_books']}
- Available copies right now: {stats['available_books']}

SECURITY & PRIVACY RULES:
1. PATRON PRIVACY PROTECTION (Role: '{user_role}'):
   - If user role is 'patron', 'user', or 'guest', NEVER display or look up another user's personal details, Ghana Card numbers, phone numbers, or loan records.
   - If asked "show overdue list" or "who has overdue books" by a patron/guest, NEVER list other patrons. State clearly: "For privacy reasons, you can only view your own overdue books."
   - Patrons can ONLY view their own account details and active loans.
   - Patrons CAN search the public book catalog and request recommendations freely.

2. LIBRARIAN & ADMIN PRIVILEGES (Role: '{user_role}'):
   - Librarians, sys_admins, and hq_admins CAN look up patron accounts by ID/Ghana Card and view full overdue reports for administrative library management.
"""

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=300
            )
        except Exception as tool_err:
            print(f"[GROQ TOOL CALL RETRY WITHOUT TOOLS] Error: {tool_err}")
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=300
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
                elif fn_name == "web_search":
                    result = web_search_online(args.get("query", ""))
                elif fn_name == "get_overdue_list":
                    result = get_overdue_list_db(db, current_user=current_user)
                elif fn_name == "get_user_by_ghana_card":
                    result = get_user_by_ghana_card_db(db, args.get("card_number", ""), current_user=current_user)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": json.dumps(result if result is not None else {"result": "None"})
                })

            second_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=300
            )
            ans = second_response.choices[0].message.content or ""
        else:
            ans = response_message.content or "Akwaaba! How can I assist you with Effutu Library resources today?"

        # Post-Processing: Clean out meta-commentary, hedging disclaimers, and timestamp dumps
        ans = re.sub(r'Based on (the )?(live )?(real-time )?(internet )?search results,?\s*', '', ans, flags=re.IGNORECASE)
        ans = re.sub(r'^it appears that\s*', '', ans, flags=re.IGNORECASE)
        ans = re.sub(r'I would recommend checking (the )?latest news sources.*', '', ans, flags=re.IGNORECASE)
        ans = re.sub(r'Current Date and Time:.*', '', ans, flags=re.IGNORECASE)
        ans = re.sub(r'web_search\s*[:\(].*?(\n|$)', '', ans, flags=re.IGNORECASE).strip()
        if ans and ans[0].islower():
            ans = ans[0].upper() + ans[1:]

        return ans or "Akwaaba! How can I assist you today at the Effutu Municipal Library Network?"

    except ImportError:
        return "Groq package not installed. Please run `pip install groq`."
    except Exception as e:
        print(f"Groq AI error: {e}")
        return f"AI Assistant temporarily offline. Please contact librarian. Error: {str(e)[:150]}"
