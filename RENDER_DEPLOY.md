# Despliegue de LXZ Store en Render

El repositorio incluye `render.yaml` para crear el servicio como **Background Worker** usando el `Dockerfile` existente. Este tipo de servicio es adecuado para un bot que mantiene una conexión de polling con Telegram y no necesita abrir un puerto web.

## Configuración

1. En Render, selecciona **New → Blueprint** y conecta el repositorio `lxzmodzxiter-coder/rayo-store-bot`.
2. Selecciona la rama `main` y aplica el Blueprint.
3. Configura `BOT_TOKEN`, `OWNER_ID` y las demás variables marcadas como secretas desde el panel de Render. Nunca las escribas en GitHub.
4. Comprueba que `DATABASE_URL` sea exactamente:

```text
sqlite+aiosqlite:////app/data/lxz_store.db
```

5. El servicio debe tener un Persistent Disk montado en `/app/data`. Solo los archivos dentro de esa ruta sobreviven a reinicios y despliegues.
6. Antes del primer despliegue, conserva una copia de la base SQLite actual. No elimines el servicio ni el disco anterior hasta confirmar que usuarios, saldos, compras, stock y baneos aparecen correctamente.

## Limitación del plan gratuito

El archivo queda preparado técnicamente para Render, pero un bot 24/7 con SQLite persistente no debe considerarse garantizado en el plan gratuito. Render documenta que el sistema de archivos normal es efímero y que el Persistent Disk se añade como recurso separado. Revisa el costo y la disponibilidad del plan antes de crear el servicio.

## Variables principales

```text
BOT_TOKEN=token_configurado_en_Render
OWNER_ID=tu_id_de_Telegram
DATABASE_URL=sqlite+aiosqlite:////app/data/lxz_store.db
CURRENCY=USD
TIMEZONE=America/Lima
SUPPORT_USERNAME=Lxz_Modz
SUPPORT_URL=https://t.me/Lxz_Modz
```

## Seguridad

No publiques tokens, claves de OpenAI, datos bancarios privados ni credenciales en el repositorio. Si un token se expuso anteriormente, revócalo en BotFather y configura uno nuevo únicamente como secreto en Render.
