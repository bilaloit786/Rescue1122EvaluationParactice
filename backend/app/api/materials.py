from io import BytesIO
from pathlib import PurePath
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import LearningMaterial, User
from app.schemas.schemas import LearningMaterialOut
from app.services.activity_service import log_activity

router = APIRouter(tags=["learning-materials"])

MAX_PDF_BYTES = 25 * 1024 * 1024
ALLOWED_PDF_CONTENT_TYPES = {
    "",
    "application/pdf",
    "application/acrobat",
    "application/octet-stream",
    "application/x-pdf",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
}


def _safe_pdf_filename(filename: str) -> str:
    safe_name = PurePath(filename or "learning-material.pdf").name
    safe_name = safe_name.replace("\r", "").replace("\n", "").replace('"', "")
    return safe_name or "learning-material.pdf"


def _material_payload(material: LearningMaterial) -> LearningMaterialOut:
    return LearningMaterialOut(
        id=material.id,
        title=material.title,
        filename=material.filename,
        content_type=material.content_type,
        file_size=material.file_size,
        uploaded_by_name=material.uploaded_by_name,
        created_at=material.created_at,
    )


@router.get("/api/materials", response_model=list[LearningMaterialOut])
async def list_materials(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    rows = await db.execute(
        select(LearningMaterial)
        .where(LearningMaterial.is_active == True)
        .order_by(desc(LearningMaterial.created_at))
    )
    return [_material_payload(material) for material in rows.scalars().all()]


@router.get("/api/materials/{material_id}/download")
async def download_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    material = await db.get(LearningMaterial, material_id)
    if not material or not material.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning material not found")

    encoded_filename = quote(material.filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        "Content-Length": str(material.file_size),
    }
    return StreamingResponse(
        BytesIO(material.file_data),
        media_type=material.content_type or "application/pdf",
        headers=headers,
    )


@router.post("/api/admin/materials", response_model=LearningMaterialOut, status_code=status.HTTP_201_CREATED)
async def upload_material(
    title: str = Form(..., min_length=2, max_length=255),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    filename = _safe_pdf_filename((file.filename or "").strip())
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a PDF")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF file is empty")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="PDF file is too large")
    if not data.lstrip()[:4] == b"%PDF":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file")

    material = LearningMaterial(
        title=title.strip(),
        filename=filename,
        content_type="application/pdf",
        file_size=len(data),
        file_data=data,
        uploaded_by_id=current_user.id,
        uploaded_by_name=current_user.username,
    )
    db.add(material)
    await db.flush()
    await log_activity(
        db,
        action="learning_material_uploaded",
        entity_type="learning_material",
        entity_id=material.id,
        actor=current_user,
        description=f"{current_user.username} uploaded learning material '{material.title}'",
        details={"filename": material.filename, "file_size": material.file_size},
    )
    await db.commit()
    await db.refresh(material)
    return _material_payload(material)


@router.delete("/api/admin/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    material = await db.get(LearningMaterial, material_id)
    if not material or not material.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning material not found")

    material.is_active = False
    db.add(material)
    await log_activity(
        db,
        action="learning_material_deleted",
        entity_type="learning_material",
        entity_id=material.id,
        actor=current_user,
        description=f"{current_user.username} removed learning material '{material.title}'",
        details={"filename": material.filename},
    )
    await db.commit()
    return None
