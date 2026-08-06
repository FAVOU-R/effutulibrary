from fastapi import APIRouter, Request, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.ai_engine import AIEngine
from app.controllers.auth_controller import get_current_user_optional
from app.models import AILog
import os

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/chat-boy")
async def chat_boy_grok(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    question = body.get("question") or body.get("prompt") or ""
    
    system_prompt = """
    You are Grok AI assistant for Effutu Municipal Library, Ghana.
    - Ghana Card format GHA-XXXXXXXXX-X
    - Auto-approval via Ghana Card, default password Effutu@XXXX, must change first login
    - Present physical Ghana Card on first visit for verification
    - Librarian can add/deactivate users at /librarian/users
    - Be helpful, concise, professional.
    """
    
    grok_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if not grok_key:
        return JSONResponse({"answer": "Grok key not found in env. Please set GROK_API_KEY on Render.", "response": "Grok key not found in env. Please set GROK_API_KEY on Render."})

    try:
        from openai import OpenAI
        client = OpenAI(api_key=grok_key, base_url="https://api.x.ai/v1")
        completion = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=400
        )
        answer = completion.choices[0].message.content
        return JSONResponse({"answer": answer, "response": answer, "prompt": question})
    except Exception as e:
        print(f"Grok error: {e}")
        err_msg = f"Grok temporarily offline. Please contact librarian. Error: {str(e)[:150]}"
        return JSONResponse({"answer": err_msg, "response": err_msg, "prompt": question})

@router.post("/chatbot")
async def chatbot_alias(request: Request):
    return await chat_boy_grok(request)

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
