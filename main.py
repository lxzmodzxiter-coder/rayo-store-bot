# ============================================================
# MAIN.PY
# RAYO FIX BOT
# PARTE 1
# ============================================================


import asyncio


from aiogram import Bot, Dispatcher


from functions import router


# Token del bot

TOKEN = "TU_TOKEN_AQUI"



# ============================================================
# INICIO DEL BOT
# ============================================================

async def main():

    bot = Bot(
        token=TOKEN
    )


    dp = Dispatcher()



    # Conectar funciones

    dp.include_router(
        router
    )



    print(
        """
⚡ RAYO FIX BOT

✅ Bot iniciado correctamente
"""
    )



    await dp.start_polling(
        bot
    )



# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
    # ============================================================
# MAIN.PY
# RAYO FIX BOT
# PARTE 2
# ============================================================


import asyncio


from aiogram import Bot, Dispatcher

from aiogram.types import BotCommand


from functions import router


from database import (
    create_tables,
    create_logs_table
)



TOKEN = "TU_TOKEN_AQUI"



# ============================================================
# COMANDOS DEL BOT
# ============================================================

async def set_commands(
    bot: Bot
):

    commands = [

        BotCommand(
            command="start",
            description="Iniciar bot"
        ),

        BotCommand(
            command="profile",
            description="Ver perfil"
        ),

        BotCommand(
            command="help",
            description="Ayuda"
        )

    ]


    await bot.set_my_commands(
        commands
    )



# ============================================================
# MAIN
# ============================================================

async def main():


    # Crear base de datos

    create_tables()

    create_logs_table()



    bot = Bot(
        token=TOKEN
    )


    dp = Dispatcher()



    dp.include_router(
        router
    )



    # Registrar comandos

    await set_commands(
        bot
    )



    print(
        """
⚡ RAYO FIX BOT

✅ Base de datos cargada
✅ Comandos configurados
✅ Bot online
"""
    )



    await dp.start_polling(
        bot
    )



# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
    # ============================================================
# MAIN.PY
# RAYO FIX BOT
# PARTE 3 FINAL
# ============================================================


import asyncio
import logging


from aiogram import Bot, Dispatcher


from functions import router


from database import (
    create_tables,
    create_logs_table
)



TOKEN = "TU_TOKEN_AQUI"



# ============================================================
# LOGS
# ============================================================

logging.basicConfig(
    level=logging.INFO
)



# ============================================================
# MANEJO DE ERRORES
# ============================================================

async def error_handler(
    event,
    exception
):

    logging.error(
        f"Error detectado: {exception}"
    )



# ============================================================
# MAIN
# ============================================================

async def main():


    # Base de datos

    create_tables()

    create_logs_table()



    bot = Bot(
        token=TOKEN
    )


    dp = Dispatcher()



    dp.include_router(
        router
    )



    # Registrar errores

    dp.errors.register(
        error_handler
    )



    try:

        print(
            """
⚡ RAYO FIX BOT

━━━━━━━━━━━━━━━━

🟢 Sistema iniciado
🗄️ Base de datos OK
🤖 Bot conectado

━━━━━━━━━━━━━━━━
"""
        )


        await dp.start_polling(
            bot
        )



    finally:


        await bot.session.close()


        print(
            """
🔴 RAYO FIX BOT

Bot detenido correctamente.
"""
        )



# ============================================================
# EJECUTAR BOT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )


    except KeyboardInterrupt:

        print(
            "Bot cerrado manualmente."
)
