import uuid
from typing import Optional, List, Union
from sqlalchemy.orm import Session
from app.database.models import Memory
from app.services.user_service import UserService


class MemoryService:
    @staticmethod
    def _to_uuid(val: Union[uuid.UUID, str]) -> uuid.UUID:
        if isinstance(val, str):
            return uuid.UUID(val)
        return val

    @staticmethod
    def create_memory(
        db: Session,
        user_id: str,
        type: str,
        key: str,
        value: str,
        importance: str = "medium",
    ) -> Memory:
        """Create a new durable memory entry, ensuring user exists."""
        UserService.get_or_create_user(db, user_id)
        memory = Memory(
            user_id=user_id,
            type=type,
            key=key,
            value=value,
            importance=importance,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def get_memory(
        db: Session, user_id: str, memory_id: Union[uuid.UUID, str]
    ) -> Optional[Memory]:
        """Retrieve a specific memory scoped by user_id."""
        mem_id = MemoryService._to_uuid(memory_id)
        return (
            db.query(Memory)
            .filter(Memory.user_id == user_id, Memory.id == mem_id)
            .first()
        )

    @staticmethod
    def list_memories(
        db: Session, user_id: str, memory_type: Optional[str] = None
    ) -> List[Memory]:
        """List all durable memories for a user, optionally filtered by type."""
        query = db.query(Memory).filter(Memory.user_id == user_id)
        if memory_type:
            query = query.filter(Memory.type == memory_type)
        return query.order_by(Memory.created_at.asc()).all()

    @staticmethod
    def update_memory(
        db: Session,
        user_id: str,
        memory_id: Union[uuid.UUID, str],
        value: Optional[str] = None,
        importance: Optional[str] = None,
    ) -> Optional[Memory]:
        """Update an existing durable memory's value and/or importance."""
        memory = MemoryService.get_memory(db, user_id, memory_id)
        if memory:
            if value is not None:
                memory.value = value
            if importance is not None:
                memory.importance = importance
            db.commit()
            db.refresh(memory)
        return memory

    @staticmethod
    def delete_memory(
        db: Session, user_id: str, memory_id: Union[uuid.UUID, str]
    ) -> bool:
        """Delete a durable memory scoped by user_id."""
        memory = MemoryService.get_memory(db, user_id, memory_id)
        if memory:
            db.delete(memory)
            db.commit()
            return True
        return False

    @staticmethod
    def upsert_memory(
        db: Session,
        user_id: str,
        type: str,
        key: str,
        value: str,
        importance: str = "medium",
    ) -> Memory:
        """
        Upsert memory based on (user_id, type, key) composite identity.
        If an existing record matches, updates value & importance; otherwise creates new.
        """
        UserService.get_or_create_user(db, user_id)
        existing = (
            db.query(Memory)
            .filter(
                Memory.user_id == user_id,
                Memory.type == type,
                Memory.key == key,
            )
            .first()
        )

        if existing:
            existing.value = value
            existing.importance = importance
            db.commit()
            db.refresh(existing)
            return existing

        return MemoryService.create_memory(
            db, user_id=user_id, type=type, key=key, value=value, importance=importance
        )
