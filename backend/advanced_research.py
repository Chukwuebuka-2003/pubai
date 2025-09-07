from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import SearchHistory
from schemas import SearchHistoryItem, SearchHistoryCreate
from routers.utils import get_current_user

import json

router = APIRouter(prefix="/advanced", tags=["advanced"])


@router.post("/", response_model=SearchHistoryItem)
def save_history(
    payload: SearchHistoryCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    articles_json = json.dumps(payload.articles)
    record = SearchHistory(
        username=current_user,
        query=payload.query,
        result_count=payload.result_count,
        articles=articles_json
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "username": record.username,
        "query": record.query,
        "result_count": record.result_count,
        "timestamp": record.timestamp,
        "articles": payload.articles
    }

@router.get("/", response_model=List[SearchHistoryItem])
def list_history(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(SearchHistory).filter(SearchHistory.username == current_user).order_by(SearchHistory.timestamp.desc()).all()
    result = []
    for r in records:
        # Ensure r.articles is treated as a string before JSON parsing
        articles_data = json.loads(str(r.articles)) if r.articles is not None else []
        result.append({
            "id": r.id,
            "username": r.username,
            "query": r.query,
            "result_count": r.result_count,
            "timestamp": r.timestamp,
            "articles": articles_data
        })
    return result

@router.get("/{history_id}", response_model=SearchHistoryItem)
def get_history_entry(
    history_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(SearchHistory).filter(SearchHistory.id == history_id, SearchHistory.username == current_user).first()
    if not r:
        raise HTTPException(status_code=404, detail="History entry not found")
    # Ensure r.articles is treated as a string before JSON parsing
    articles_data = json.loads(str(r.articles)) if r.articles is not None else []
    return {
        "id": r.id,
        "username": r.username,
        "query": r.query,
        "result_count": r.result_count,
        "timestamp": r.timestamp,
        "articles": articles_data
    }

@router.delete("/{history_id}")
def delete_history_entry(
    history_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(SearchHistory).filter(SearchHistory.id == history_id, SearchHistory.username == current_user).delete()
    db.commit()
    if count:
        return {"message": "Deleted"}
    else:
        raise HTTPException(status_code=404, detail="Entry not found")

@router.delete("/")
def clear_all_history(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(SearchHistory).filter(SearchHistory.username == current_user).delete()
    db.commit()
    return {"message": f"Deleted {count} entries"}
