from fastapi import APIRouter, Depends, Query, Request, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai_engine import AIEngine
from app.controllers.auth_controller import get_current_user_optional, get_current_user
from app.models import AILog

router = APIRouter(tags=["AI Features"])

@router.get("/api/search")
def nlp_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    AI Feature 3: NLP Search endpoint (/api/search?q=)
    """
    results = AIEngine.nlp_search(db, q)
    return JSONResponse(content={"query": q, "total_matches": len(results), "results": results})

@router.get("/api/ai/recommend")
def get_recommendations(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    AI Feature 1: Collaborative Filtering Recommendation
    """
    user = get_current_user_optional(request, db)
    user_id = user.id if user else 1
    recs = AIEngine.get_collaborative_recommendations(db, user_id=user_id, limit=6)
    return JSONResponse(content={"recommendations": recs})

@router.get("/api/ai/predict-demand")
def predict_demand(db: Session = Depends(get_db)):
    """
    AI Feature 2: Predictive Demand Forecasting for Exam Season
    """
    forecast = AIEngine.predict_exam_demand(db)
    return JSONResponse(content=forecast)

@router.post("/api/ai/chatbot")
def chatbot_interaction(
    payload: dict = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    prompt = payload.get("prompt", "")
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "Prompt string is required"})

    user = get_current_user_optional(request, db)
    response_text = AIEngine.generate_chatbot_response(db, prompt, user)

    # Log query
    log = AILog(
        user_id=user.id if user else None,
        query=prompt,
        intent="chatbot_query",
        response=response_text
    )
    db.add(log)
    db.commit()

    return JSONResponse(content={"prompt": prompt, "response": response_text})
