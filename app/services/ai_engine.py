from sqlalchemy.orm import Session
from app.models import Book, BookCopy, Transaction, AILog
from datetime import datetime, timedelta

class AIEngine:
    @staticmethod
    def nlp_search(db: Session, query: str):
        query_clean = query.lower().strip()
        books = db.query(Book).all()
        results = []
        for b in books:
            if query_clean in b.title.lower() or query_clean in b.author.lower() or query_clean in b.category.lower() or (b.description and query_clean in b.description.lower()):
                results.append({
                    "id": b.id,
                    "title": b.title,
                    "author": b.author,
                    "category": b.category,
                    "isbn": b.isbn
                })
        return results

    @staticmethod
    def get_collaborative_recommendations(db: Session, user_id: int, limit: int = 6):
        if not db:
            return []

        from app.models import Transaction, Reservation, AILog, Book
        borrowed_book_ids = set()
        category_weights = {}

        # 1. Study User Borrowing History (Weight = 5 points per loan)
        try:
            txs = db.query(Transaction).filter(Transaction.patron_id == user_id).all()
            for tx in txs:
                if tx.book_copy and tx.book_copy.book:
                    b = tx.book_copy.book
                    borrowed_book_ids.add(b.id)
                    cat = (b.category or "General").title()
                    category_weights[cat] = category_weights.get(cat, 0) + 5
        except Exception as tx_err:
            print(f"Error studying user borrowing history: {tx_err}")

        # 2. Study User Reservation History (Weight = 4 points per reservation)
        try:
            res_list = db.query(Reservation).filter(Reservation.user_id == user_id).all()
            for r in res_list:
                if r.book:
                    borrowed_book_ids.add(r.book.id)
                    cat = (r.book.category or "General").title()
                    category_weights[cat] = category_weights.get(cat, 0) + 4
        except Exception as res_err:
            print(f"Error studying user reservation history: {res_err}")

        # 3. Study User AI Search & Chat Log History (Weight = 2 points per query match)
        try:
            logs = db.query(AILog).filter(AILog.user_id == user_id).all()
            all_books = db.query(Book).all()
            for log in logs:
                q_lower = (log.query or "").lower()
                for b in all_books:
                    if b.category and b.category.lower() in q_lower:
                        cat = b.category.title()
                        category_weights[cat] = category_weights.get(cat, 0) + 2
                    elif b.title and any(w in q_lower for w in b.title.lower().split() if len(w) > 3):
                        cat = (b.category or "General").title()
                        category_weights[cat] = category_weights.get(cat, 0) + 1
        except Exception as log_err:
            print(f"Error studying user AI logs: {log_err}")

        # Sort categories by interest score studied over time
        top_cats = sorted(category_weights.keys(), key=lambda c: category_weights[c], reverse=True)

        recommended_books = []
        added_ids = set()

        # Step A: Pick unread books from user's studied interest categories
        if top_cats:
            for cat in top_cats:
                cat_books = db.query(Book).filter(
                    Book.category.ilike(f"%{cat}%"),
                    ~Book.id.in_(borrowed_book_ids) if borrowed_book_ids else True,
                    ~Book.id.in_(added_ids) if added_ids else True
                ).limit(limit - len(recommended_books)).all()

                for b in cat_books:
                    recommended_books.append((b, f"Studied interest in {cat}"))
                    added_ids.add(b.id)

                if len(recommended_books) >= limit:
                    break

        # Step B: Fill remaining slots with unread general catalog & WASSCE prep books
        if len(recommended_books) < limit:
            remaining = db.query(Book).filter(
                ~Book.id.in_(borrowed_book_ids) if borrowed_book_ids else True,
                ~Book.id.in_(added_ids) if added_ids else True
            ).limit(limit - len(recommended_books)).all()

            for b in remaining:
                recommended_books.append((b, "Top Recommended Library Read"))
                added_ids.add(b.id)

        res = []
        for b, reason in recommended_books[:limit]:
            res.append({
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "category": b.category,
                "reason": reason,
                "cover_url": b.cover_url or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300"
            })
        return res

    @staticmethod
    def predict_exam_demand(db: Session):
        wassce_books = db.query(Book).filter(Book.category == "WASSCE").all()
        return {
            "season": "WASSCE Exam Season Prep",
            "forecast_period_days": 30,
            "high_demand_count": len(wassce_books),
            "recommendation": "Stock additional copies at Winneba Central HQ & Community Library branches."
        }

    @staticmethod
    def generate_chatbot_response(db: Session, prompt: str, user=None):
        return f"Effutu Library AI Assistant response to: {prompt}"
