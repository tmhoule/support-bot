import uuid
from datetime import datetime, UTC
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.models import Conversation, Message


def _new_id() -> str:
    return uuid.uuid4().hex


class ConversationRepository:
    def __init__(self, session: Session):
        self.s = session

    def create_conversation(self, tech_name: str) -> Conversation:
        c = Conversation(id=_new_id(), tech_name=tech_name)
        self.s.add(c)
        self.s.commit()
        return c

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.s.get(Conversation, conversation_id)

    def touch(self, conversation_id: str) -> None:
        c = self.get_conversation(conversation_id)
        if c:
            c.last_active = datetime.now(UTC)
            self.s.commit()

    def add_message(self, conversation_id: str, role: str, content: dict) -> Message:
        m = Message(id=_new_id(), conversation_id=conversation_id, role=role, content_json=content)
        self.s.add(m)
        self.touch(conversation_id)
        self.s.commit()
        return m

    def list_messages(self, conversation_id: str) -> list[Message]:
        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.id)
        return list(self.s.scalars(stmt))

    def list_conversations(self, limit: int = 50, offset: int = 0, name_filter: str | None = None) -> list[Conversation]:
        stmt = select(Conversation).order_by(desc(Conversation.last_active)).limit(limit).offset(offset)
        if name_filter:
            stmt = stmt.where(Conversation.tech_name.ilike(f"%{name_filter}%"))
        return list(self.s.scalars(stmt))
