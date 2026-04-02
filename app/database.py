from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_engine(
    url=settings.get_sync_db_url,
    echo=True,
)

async_engine = create_async_engine(
    url=settings.get_async_db_url,
    echo=True,
    pool_size=5,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_session():
    async with async_session_factory() as session:
        yield session


async def test_session(session):
    try:
        async with session() as session:
            # Выполняем запрос
            await session.execute(text("SELECT 1"))
        print("✅ Сессия работает, база данных отвечает.")
    except Exception as e:
        print(f"❌ Не удалось создать сессию: {e}")