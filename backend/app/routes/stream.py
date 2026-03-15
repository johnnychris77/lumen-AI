from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.deps import get_db
from app.db import models
from app.ai.inference import LumenAIModel

router = APIRouter(tags=["stream"])

model = LumenAIModel()

@router.post("/stream/frame")
async def process_frame(
    frame: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    image_bytes = await frame.read()

    result = model.predict(image_bytes)

    inspection = models.Inspection(
        file_name=frame.filename,
        stain_detected=result["stain_detected"],
        confidence=result["confidence"],
        material_type=result["material_type"],
        instrument_type=result["instrument_type"],
        detected_issue=result["detected_issue"],
        inference_mode=result["inference_mode"],
        model_name=result["model_name"],
        model_version=result["model_version"],
        status="completed"
    )

    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return {
        "inspection_id": inspection.id,
        "result": result
    }
