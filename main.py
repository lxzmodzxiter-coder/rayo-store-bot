import asyncio
import logging
import os
from threading import Thread

from flask import Flask

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import init_db
from functions import router


# ==========================================
# CONFIGURACIÓN
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ==========================================
# FLASK (RENDER)
# ==========================================

app = Flask(__name__)


@app.route("/")
def home():
    return "⚡ RAYO FIX STORE ONLINE"


def run_web():
    port = int(os.getenv("PORT", "10000"))
    app.run(
        host="0.0.0.0",
        port=port
    )


Thread(
    target=run_web,
    daemon=True
).start()


# ==========================================
# BOT
# ==========================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

dp.include_router(router)


# ==========================================
# INICIO
# ==========================================

async def main():

    logger.info("Iniciando base de datos...")

    init_db()

    logger.info("Base de datos iniciada.")

    logger.info("Bot iniciado correctamente.")

    await dp.start_polling(bot)


# ==========================================
# EJECUCIÓN
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except (KeyboardInterrupt, SystemExit):

        logger.info("Bot detenido.")
