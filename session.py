from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from config import settings  # Importa directamente del archivo config.py que acabas de crear

# Creamos el motor de conexión a la base de datos
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,       # Soporta 20 conexiones simultáneas
    max_overflow=10,    # Y 10 extra si hay picos de usuarios
    pool_pre_ping=True  # Verifica que la conexión no se haya caído
)

# Creamos el generador de sesiones
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

