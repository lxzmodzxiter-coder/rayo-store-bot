# Despliegue de LXZ Store en Railway

El proyecto usa el `Dockerfile` de la raíz y arranca con `python bot.py`. Railway detecta el Dockerfile automáticamente al conectar el repositorio de GitHub.

## Configuración recomendada

1. Crea o conserva el servicio existente de Railway y conecta el repositorio `lxzmodzxiter-coder/rayo-store-bot`.
2. Selecciona la rama `main` y activa el despliegue automático.
3. Añade un **Volume** al servicio y monta el volumen exactamente en `/app/data`.
4. Configura esta variable de entorno:

```text
DATABASE_URL=sqlite+aiosqlite:////app/data/lxz_store.db
```

5. Configura `BOT_TOKEN`, `OWNER_ID`, `OPENAI_API_KEY` y los demás valores privados desde Variables de Railway. Nunca los guardes en GitHub.
6. Haz el primer deploy y revisa los logs. El proceso esperado es `python bot.py`.

## Persistencia

La base de datos solo se conserva si el Volume permanece asociado al mismo servicio y `DATABASE_URL` apunta a `/app/data/lxz_store.db`. No elimines ni recrees el servicio o el Volume para actualizar el código. Cada despliegue desde `main` debe reutilizar el mismo almacenamiento.

Antes de cambiar el servicio, realiza una copia de seguridad del archivo `lxz_store.db`. Comprueba después del deploy que sigan presentes los usuarios, saldos, compras, stock, rangos y baneos.

## Variables esenciales

```text
BOT_TOKEN=secreto_de_Railway
OWNER_ID=tu_id_de_Telegram
DATABASE_URL=sqlite+aiosqlite:////app/data/lxz_store.db
STORE_NAME=LXZ STORE BEST
CURRENCY=USD
TIMEZONE=America/Lima
SUPPORT_USERNAME=Lxz_Modz
SUPPORT_URL=https://t.me/Lxz_Modz

# Pagos de Perú
YAPE_NUMBER=...
YAPE_NAME=...
LIGO_NUMBER=...
LIGO_NAME=...
PLIN_NUMBER=...
PLIN_NAME=...
```

`OWNER_ID` debe contener únicamente tu ID numérico de Telegram. Configura los números y nombres de pago de Perú como variables privadas (`YAPE_NUMBER`, `YAPE_NAME`, `LIGO_NUMBER`, `LIGO_NAME`, `PLIN_NUMBER` y `PLIN_NAME`) para que el bot los muestre sin guardarlos en GitHub. No compartas el token del bot, claves de OpenAI ni credenciales de pagos por chat.
