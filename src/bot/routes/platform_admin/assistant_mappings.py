"""Admin APIs for assistant-to-bot mappings."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bot.deps import AsyncSessionLocal
from bot.models.assistant_mappings import AssistantMapping

router = APIRouter()


class AssistantMappingResponse(BaseModel):
    """Response schema for assistant mappings."""

    id: UUID
    assistant_id: str
    bot_id: UUID
    created_at: datetime | None
    updated_at: datetime | None


class AssistantMappingCreate(BaseModel):
    assistant_id: str
    bot_id: UUID


class AssistantMappingUpdate(BaseModel):
    assistant_id: str | None = None
    bot_id: UUID | None = None


def _to_response(mapping: AssistantMapping) -> AssistantMappingResponse:
    return AssistantMappingResponse(
        id=mapping.id,
        assistant_id=mapping.assistant_id,
        bot_id=mapping.bot_id,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
    )


@router.get("/", response_model=List[AssistantMappingResponse])
async def list_mappings():
    """List assistant->bot mappings."""
    async with AsyncSessionLocal() as session:
        stmt = select(AssistantMapping).order_by(AssistantMapping.created_at.desc())
        result = await session.execute(stmt)
        mappings = result.scalars().all()
        return [_to_response(mapping) for mapping in mappings]


@router.post("/", response_model=AssistantMappingResponse)
async def create_mapping(request: AssistantMappingCreate):
    """Create a new mapping."""
    async with AsyncSessionLocal() as session:
        mapping = AssistantMapping(
            assistant_id=request.assistant_id,
            bot_id=request.bot_id,
        )
        session.add(mapping)
        try:
            await session.commit()
            await session.refresh(mapping)
            return _to_response(mapping)
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail="assistant_id already registered. delete or update the existing mapping first.",
            )


@router.get("/{mapping_id}", response_model=AssistantMappingResponse)
async def get_mapping(mapping_id: UUID):
    """Fetch a single mapping."""
    async with AsyncSessionLocal() as session:
        mapping = await session.get(AssistantMapping, mapping_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not found.")
        return _to_response(mapping)


@router.put("/{mapping_id}", response_model=AssistantMappingResponse)
async def update_mapping(mapping_id: UUID, request: AssistantMappingUpdate):
    """Update an existing mapping."""
    if not request.assistant_id and not request.bot_id:
        raise HTTPException(
            status_code=400,
            detail="At least one of assistant_id or bot_id must be provided.",
        )
    async with AsyncSessionLocal() as session:
        mapping = await session.get(AssistantMapping, mapping_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not found.")
        if request.assistant_id is not None:
            mapping.assistant_id = request.assistant_id
        if request.bot_id is not None:
            mapping.bot_id = request.bot_id
        try:
            await session.commit()
            await session.refresh(mapping)
            return _to_response(mapping)
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail="assistant_id already registered. choose a different assistant_id.",
            )


@router.delete("/{mapping_id}")
async def delete_mapping(mapping_id: UUID):
    """Delete a mapping."""
    async with AsyncSessionLocal() as session:
        mapping = await session.get(AssistantMapping, mapping_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not found.")
        await session.delete(mapping)
        await session.commit()
        return {"deleted": True}
