import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.config import settings


def _make_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(
        url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=300,
    )


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class GUID(TypeDecorator):
    """Platform-independent GUID type — UUID on PostgreSQL, CHAR(36) on SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(str(value))


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)
    user_metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=[])
    artifact = Column(JSON, nullable=True)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="messages")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
