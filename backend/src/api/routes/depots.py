"""Read-only depot discovery for the dispatch optimization UI."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import Depot

router = APIRouter()


@router.get("")
async def list_depots(db: AsyncSession = Depends(get_db)):
    """Return active depots; never invent depot IDs in the client."""
    result = await db.execute(
        select(Depot).where(Depot.is_active.is_(True)).order_by(Depot.name)
    )
    return {
        "depots": [
            {
                "id": str(depot.id),
                "name": depot.name,
                "address": depot.address,
                "latitude": float(depot.latitude),
                "longitude": float(depot.longitude),
            }
            for depot in result.scalars().all()
        ]
    }
