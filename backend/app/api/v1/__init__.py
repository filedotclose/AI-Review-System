from fastapi import APIRouter
from app.api.v1 import auth, dpr, fuel, petty_cash, attendance, brief

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dpr.router, prefix="/dpr", tags=["dpr"])
api_router.include_router(fuel.router, prefix="/fuel", tags=["fuel"])
api_router.include_router(fuel.router, prefix="/fuel-register", tags=["fuel"])

# Petty Cash Management (Milestone 3)
api_router.include_router(petty_cash.router, prefix="/petty-cash", tags=["petty-cash"])
api_router.include_router(petty_cash.router, prefix="/petty_cash", tags=["petty-cash"])
api_router.include_router(petty_cash.router, tags=["petty-cash"])

# Attendance Tracking (Milestone 4)
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(attendance.router, tags=["attendance"])

# Executive Brief (Milestone 5)
api_router.include_router(brief.router, prefix="/brief", tags=["brief"])

__all__ = ["api_router", "auth", "dpr", "fuel", "petty_cash", "attendance", "brief"]


