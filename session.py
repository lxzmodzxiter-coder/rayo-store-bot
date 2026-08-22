from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

engine_kwargs = {"echo": False, "pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.pop("pool_pre_ping", None)
else:
    engine_kwargs.update(pool_size=20, max_overflow=10)

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
async_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
