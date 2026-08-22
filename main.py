import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

import start
from auth import AuthMiddleware

# Importamos nuestros propios archivos y modelos
from config import settings
from database import Base, DatabaseMiddleware, engine

# Configuración para ver errores y mensajes en la consola de Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main() -> None:
    # 0. Creamos las tablas en PostgreSQL automáticamente si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("📦 Tablas de la base de datos verificadas/creadas con éxito.")

    # 1. Conexión a Redis
    redis_client = Redis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis=redis_client)

    # 2. Inicializamos el Bot de Telegram
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    # 3. Activamos los guardias de seguridad (Middlewares)
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AuthMiddleware())

    # 4. Registramos los comandos (nuestro archivo start.py)
    dp.include_router(start.router)

    logger.info("⚡ LXZ STORE BEST iniciado correctamente en modo producción.")
    
    try:
        # 5. Ponemos al bot a escuchar a los usuarios
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Apagado seguro si se reinicia el servidor
        await bot.session.close()
        await redis_client.aclose()
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido manualmente.")
        
