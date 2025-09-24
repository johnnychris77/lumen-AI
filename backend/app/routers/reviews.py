from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import random, time

from backend.app.core.auth_dep import require_reviewer

router = APIRouter(prefix="/reviews", tags=["reviews"])

class Frame(BaseModel):
    key: str
    url: Optional[str] = None

class ReviewItem(BaseModel):
    id: int
    instrument_id: Optional[str] = None
    tray_id: Optional[str] = None
    confidence: Optional[float] = None
    frames: List[Frame] = []
    result_json: Optional[dict] = None

QUEUE: list[ReviewItem] = []
NEXT_ID = 1

@router.post("/seed", dependencies=[Depends(require_reviewer)])
def seed_queue(n: int = Query(5, ge=1, le=50)):
    global NEXT_ID
    for _ in range(n):
        rid = NEXT_ID; NEXT_ID += 1
        conf = round(random.uniform(0.45, 0.7), 3)
        frames = [
            Frame(key=f"demo/{rid}/frame1.jpg", url=f"https://picsum.photos/seed/{rid}1/640/360"),
            Frame(key=f"demo/{rid}/frame2.jpg", url=f"https://picsum.photos/seed/{rid}2/640/360"),
        ]
        QUEUE.append(ReviewItem(
            id=rid,
            instrument_id=f"INST-{random.randint(100,999)}",
            tray_id=f"TRAY-{random.randint(100,999)}",
            confidence=conf,
            frames=frames,
            result_json={"pred":"bioburden" if conf<0.6 else "rust", "ts": int(time.time())}
        ))
    return {"seeded": n, "total": len(QUEUE)}

@router.get("/queue", response_model=list[ReviewItem], dependencies=[Depends(require_reviewer)])
def get_queue():
    return QUEUE

class FeedbackIn(BaseModel):
    decision: str
    correct_class: Optional[str] = None
    notes: Optional[str] = None

@router.post("/{analysis_id}/feedback", dependencies=[Depends(require_reviewer)])
def post_feedback(analysis_id: int, body: FeedbackIn):
    for i, item in enumerate(QUEUE):
        if item.id == analysis_id:
            QUEUE.pop(i)
            return {"ok": True, "removed": analysis_id, "decision": body.decision}
    raise HTTPException(status_code=404, detail="not found")
