from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.models.user import User, StaffProfile
from app.schemas.schemas import ChangePasswordRequest, RegisterRequest, TokenResponse, UserOut
from app.services.activity_service import get_request_access_details, log_activity

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
DUMMY_PASSWORD_HASH = get_password_hash("dummy-password-for-timing-check")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    password_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(form.password, password_hash)
    if not user or not password_valid:
        await log_activity(
            db,
            action="login_failed",
            entity_type="auth",
            description=f"Failed login attempt for username '{form.username}'",
            details={"username": form.username, **get_request_access_details(request)},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    token = create_access_token({"sub": str(user.id)})
    await log_activity(
        db,
        action="login_success",
        entity_type="staff" if user.role == "staff" else "admin",
        entity_id=user.id,
        actor=user,
        description=f"{user.username} signed in",
        details=get_request_access_details(request),
    )
    await db.commit()
    return TokenResponse(access_token=token, token_type="bearer", role=user.role, user_id=user.id)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already registered")

    try:
        hashed_password = get_password_hash(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed_password,
        role="staff",
    )
    db.add(user)
    await db.flush()

    profile = StaffProfile(
        user_id=user.id,
        full_name=payload.full_name,
        father_name=payload.father_name,
        designation=payload.designation,
        district=payload.district,
        station=payload.station,
        employee_id=payload.employee_id,
        phone=payload.phone,
    )
    db.add(profile)
    await log_activity(
        db,
        action="user_registered",
        entity_type="staff",
        entity_id=user.id,
        description=f"{payload.full_name} registered a staff account",
        details={
            "username": payload.username,
            "designation": payload.designation,
            "district": payload.district,
            **get_request_access_details(request),
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    return user


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    try:
        user.hashed_password = get_password_hash(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await log_activity(
        db,
        action="password_changed",
        entity_type="staff" if user.role == "staff" else "admin",
        entity_id=user.id,
        actor=user,
        description=f"{user.username} changed password",
        details=get_request_access_details(request),
    )
    await db.commit()
    return {"message": "Password changed successfully"}
