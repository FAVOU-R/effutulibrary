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
        books = db.query(Book).limit(limit).all()
        return [{
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "category": b.category,
            "cover_url": b.cover_url or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300"
        } for b in books]

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
