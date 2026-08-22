# ⚡ LXZ STORE BEST

Bot de ventas para Telegram construido con **aiogram 3**, **PostgreSQL/SQLite mediante SQLAlchemy async** y **Redis** para los estados FSM. El proyecto contiene flujos funcionales para catálogo, búsqueda, compra con bloqueo de filas, saldo, recargas con comprobante, cupones, referidos, Premium, perfiles, historial, administración, difusión y auditoría.

## Configuración

Copia `.env.example` a `.env` y completa al menos `BOT_TOKEN`, `OWNER_ID`, `DATABASE_URL` y `REDIS_URL`. Para producción se recomienda PostgreSQL con una URL `postgresql+asyncpg://...` y Redis administrado. Yape/Plin y Binance solo se muestran cuando están configurados; no se presentan botones para métodos inexistentes.

`ADMIN_IDS` acepta una lista separada por comas. El `OWNER_ID` siempre conserva el nivel Owner y no puede degradarse desde el panel. El bot crea las tablas al iniciar, pero en una instalación con datos existentes se debe respaldar la base de datos y revisar cualquier cambio de esquema antes de desplegar.

## Ejecución local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python main.py
```

También se puede usar el entorno incluido en `docker-compose.yml`, proporcionando primero el archivo `.env`.

## Seguridad y operación

Las operaciones de compra y aprobación de recargas se validan nuevamente en el servidor, comprueban permisos y estado actual, y usan bloqueo de fila para evitar dobles acciones. Los datos de entrega se asocian al pedido del comprador y los comprobantes se notifican al personal configurado. Las operaciones administrativas sensibles requieren confirmación, registran auditoría y nunca incluyen tokens en los logs.

Las pruebas de sintaxis y el smoke test de importación, esquema y registro de handlers se ejecutan sin contactar Telegram ni requerir credenciales reales.
