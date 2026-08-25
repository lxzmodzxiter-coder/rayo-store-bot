# Monitor autorizado de canales de WhatsApp

Este servicio complementario observa, mediante una sesión autorizada de WhatsApp Web, seis canales públicos y reenvía a Telegram únicamente las publicaciones cuyo texto contiene `MediaFire` (la comparación no distingue mayúsculas y minúsculas, y acepta `Media-Fire` o `Media_Fire`).

Cuando la publicación incluye una imagen u otro archivo multimedia, el monitor envía el archivo y conserva el texto completo como pie de foto cuando Telegram lo permite. Si el texto supera el límite de pie de foto de Telegram, envía el archivo y después el resto del texto en mensajes separados. Cuando no hay multimedia, envía todo el texto dividido solo si supera el límite de Telegram. Un archivo de estado persistente evita reenviar dos veces la misma publicación.

## Canales configurados

| Canal | Enlace público |
|---|---|
| DripClient Update - Att | https://whatsapp.com/channel/0029VbAsXxm6RGJMuXL1RA1P |
| HG-CHEATS Update - Att | https://whatsapp.com/channel/0029VbBHFBbJkK76AQmq3p3D |
| Holograma Updates - Att | https://whatsapp.com/channel/0029VbBks2cCsU9Iq6WHw135 |
| 𝙅𝙊𝙀𝙇 𝙈𝙊𝘿𝙎 ✅ | https://whatsapp.com/channel/0029Vb6BlwVISTkEKGAI3F3W |
| Monite Updates - Att | https://whatsapp.com/channel/0029VbCeewM7tkj2eJlxpd39 |
| 🔥 𝙃𝙂 𝘾𝙃𝙀𝘼𝙏𝙎 𝙐𝙋𝘿𝘼𝙏𝙀𝙎 - 𝙋𝙍𝙊𝙈𝙊𝘾̧𝙊̃𝙀𝙎 🔥 | https://whatsapp.com/channel/0029Vb6FTtpGE56fIpK5p00E |

## Requisitos

El monitor no debe ejecutarse dentro del mismo servicio ligero de Python que aloja el bot en Railway gratuito. Necesita Node.js, Chromium y almacenamiento persistente para la sesión de WhatsApp y el estado de deduplicación. Puede ejecutarse en una computadora que permanezca encendida, un VPS o un servicio de contenedores con volumen persistente.

Copia `.env.whatsapp-monitor.example` a un archivo de entorno privado y define `TELEGRAM_BOT_TOKEN` y `TELEGRAM_TARGET_CHAT_ID`. El destino debe ser un chat, grupo o canal de Telegram donde el bot tenga permiso para publicar. No guardes el token en GitHub.

Para probarlo localmente, ejecuta `npm install` y luego `npm start`. Con `WHATSAPP_HEADLESS=false` aparecerá el navegador; escanea el QR desde **WhatsApp → Ajustes → Dispositivos vinculados → Vincular un dispositivo**. Después de que aparezca `Monitor activo`, puedes cerrar la ventana visual si el proceso continúa en segundo plano. La primera vinculación genera una carpeta `.wwebjs_auth`; esa carpeta y `data/` deben permanecer en un volumen persistente.

Para un despliegue con Docker, usa `Dockerfile.whatsapp-monitor` como Dockerfile del servicio independiente y monta un volumen en `/app/.wwebjs_auth` y otro en `/app/data`. La primera ejecución debe hacerse con `WHATSAPP_HEADLESS=false` para vincular la sesión; después puede cambiarse a `true` si el proveedor permite completar la vinculación de forma segura.

## Límites y seguridad

Esta integración utiliza WhatsApp Web y una librería no oficial; puede dejar de funcionar cuando WhatsApp cambie su interfaz y puede activar restricciones de cuenta. Usa una cuenta dedicada si es posible. El monitor solo filtra los seis canales configurados y no envía mensajes a WhatsApp ni lee conversaciones privadas intencionadamente.

No existe un webhook oficial de Meta para recibir publicaciones nuevas de canales. La documentación oficial de WhatsApp Business Platform describe webhooks para mensajes enviados a un negocio, estados y eventos de cuenta, no un evento de publicaciones de canales. Por eso esta solución no debe presentarse como una integración oficial de Meta.

La activación del monitor no publica automáticamente archivos en el catálogo ni modifica precios, stock o saldo. Solo reenvía publicaciones que contengan `MediaFire` al destino de Telegram configurado.
