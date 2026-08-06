from fastapi import APIRouter, Request, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai_engine import AIEngine
from app.controllers.auth_controller import get_current_user_optional
from app.models import AILog
import os

from app.services.ai_service import get_ai_response

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/chat-boy")
async def chat_boy_grok(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    question = body.get("question") or body.get("prompt") or ""
    answer = get_ai_response(question, db=db)
    return JSONResponse({"answer": answer, "response": answer, "prompt": question})

@router.post("/chatbot")
async def chatbot_alias(request: Request, db: Session = Depends(get_db)):
    return await chat_boy_grok(request, db=db)

@router.get("/search")
def nlp_search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    results = AIEngine.nlp_search(db, q)
    return JSONResponse(content={"query": q, "total_matches": len(results), "results": results})

@router.get("/recommend")
def get_recommendations(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    user_id = user.id if user else 1
    recs = AIEngine.get_collaborative_recommendations(db, user_id=user_id, limit=6)
    return JSONResponse(content={"recommendations": recs})

@router.get("/predict-demand")
def predict_demand(db: Session = Depends(get_db)):
    forecast = AIEngine.predict_exam_demand(db)
    return JSONResponse(content=forecast)
