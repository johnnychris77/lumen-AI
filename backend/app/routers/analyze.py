from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import hashlib, time

from backend.app.routers.reviews import QUEUE, ReviewItem, Frame, NEXT_ID

router = APIRouter(tags=["analyze"])

class AnalyzeOut(BaseModel):
    predicted: str
    confidence: float
    review_id: int | None = None

CLASSES = ["clean", "bioburden", "rust"]

@router.post("/analyze", response_model=AnalyzeOut)
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    h = int(hashlib.sha256(data).hexdigest(), 16)
    predicted = CLASSES[h % len(CLASSES)]
    confidence = 0.55 + ((h % 30) / 100)  # 0.55 .. 0.84

    review_id = None
    if confidence < 0.65:
        global NEXT_ID
        rid = NEXT_ID; NEXT_ID += 1
        QUEUE.append(ReviewItem(
            id=rid,
            instrument_id="INST-ANALYZE",
            tray_id="TRAY-ANALYZE",
            confidence=round(confidence,3),
            frames=[Frame(key=f"upload/{rid}/frame1.jpg", url="https://picsum.photos/seed/upload/640/360")],
            result_json={"pred": predicted, "ts": int(time.time())}
        ))
        review_id = rid

    return AnalyzeOut(predicted=predicted, confidence=round(confidence,3), review_id=review_id)
