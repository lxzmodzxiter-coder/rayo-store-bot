const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");

const qrcode = require("qrcode-terminal");
const { Client, LocalAuth } = require("whatsapp-web.js");

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || "";
const TELEGRAM_TARGET_CHAT_ID = process.env.TELEGRAM_TARGET_CHAT_ID || "";
const AUTH_PATH = process.env.WHATSAPP_AUTH_PATH || "./.wwebjs_auth";
const STATE_FILE = process.env.STATE_FILE || "./data/seen_mediafire.json";
const MAX_SEEN = Number.parseInt(process.env.MAX_SEEN || "5000", 10);
const MEDIAFIRE_PATTERN = /media\s*[-_]?\s*fire/i;

const CHANNELS = new Map([
  ["0029VbAsXxm6RGJMuXL1RA1P", "DripClient Update - Att"],
  ["0029VbBHFBbJkK76AQmq3p3D", "HG-CHEATS Update - Att"],
  ["0029VbBks2cCsU9Iq6WHw135", "Holograma Updates - Att"],
  ["0029Vb6BlwVISTkEKGAI3F3W", "𝙅𝙊𝙀𝙇 𝙈𝙊𝘿𝙎 ✅"],
  ["0029VbCeewM7tkj2eJlxpd39", "Monite Updates - Att"],
  ["0029Vb6FTtpGE56fIpK5p00E", "🔥 𝙃𝙂 𝘾𝙃𝙀𝘼𝙏𝙎 𝙐𝙋𝘿𝘼𝙏𝙀𝙎 - 𝙋𝙍𝙊𝙈𝙊𝘾̧𝙊̃𝙀𝙎 🔥"],
]);

const seen = new Set();
const inFlight = new Set();
let saveQueue = Promise.resolve();

function requireConfig() {
  const missing = [];
  if (!TELEGRAM_BOT_TOKEN) missing.push("TELEGRAM_BOT_TOKEN");
  if (!TELEGRAM_TARGET_CHAT_ID) missing.push("TELEGRAM_TARGET_CHAT_ID");
  if (missing.length) {
    throw new Error(`Faltan variables obligatorias: ${missing.join(", ")}`);
  }
}

async function ensureParent(filePath) {
  await fs.mkdir(path.dirname(path.resolve(filePath)), { recursive: true });
}

async function loadSeen() {
  try {
    const raw = await fs.readFile(STATE_FILE, "utf8");
    const values = JSON.parse(raw);
    if (Array.isArray(values)) values.slice(-MAX_SEEN).forEach((value) => seen.add(value));
  } catch (error) {
    if (error.code !== "ENOENT") console.warn("No se pudo cargar el estado de deduplicación:", error.message);
  }
}

function remember(key) {
  seen.add(key);
  while (seen.size > MAX_SEEN) seen.delete(seen.values().next().value);
  saveQueue = saveQueue
    .then(async () => {
      await ensureParent(STATE_FILE);
      const temporary = `${STATE_FILE}.tmp`;
      await fs.writeFile(temporary, JSON.stringify([...seen]), "utf8");
      await fs.rename(temporary, STATE_FILE);
    })
    .catch((error) => console.error("No se pudo guardar el estado de deduplicación:", error.message));
  return saveQueue;
}

function shouldForward(text) {
  return Boolean(text && MEDIAFIRE_PATTERN.test(text));
}

function messageKey(message, channelName, text) {
  const serialized = message.id?._serialized || `${message.timestamp || "0"}:${message.from || ""}`;
  return crypto.createHash("sha256").update(`${channelName}:${serialized}:${text}`).digest("hex");
}

function chunks(text, limit = 4096) {
  const result = [];
  let remaining = text;
  while (remaining.length > limit) {
    let cut = remaining.lastIndexOf("\n", limit);
    if (cut < Math.floor(limit * 0.5)) cut = limit;
    result.push(remaining.slice(0, cut));
    remaining = remaining.slice(cut).replace(/^\n+/, "");
  }
  if (remaining) result.push(remaining);
  return result.length ? result : [""];
}

async function telegramRequest(method, body) {
  const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    body,
  });
  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(`Telegram ${method} falló: ${payload.description || response.statusText}`);
  }
  return payload.result;
}

async function sendText(text) {
  for (const part of chunks(text)) {
    const form = new FormData();
    form.append("chat_id", TELEGRAM_TARGET_CHAT_ID);
    form.append("text", part);
    await telegramRequest("sendMessage", form);
  }
}

async function sendMedia(media, text) {
  const bytes = Buffer.from(media.data, "base64");
  const mime = media.mimetype || "application/octet-stream";
  const filename = media.filename || (mime.startsWith("image/") ? "actualizacion.jpg" : "actualizacion.bin");
  const caption = text.length <= 1024 ? text : "";
  const form = new FormData();
  form.append("chat_id", TELEGRAM_TARGET_CHAT_ID);
  form.append(mime.startsWith("image/") ? "photo" : "document", new Blob([bytes], { type: mime }), filename);
  if (caption) form.append("caption", caption);
  await telegramRequest(mime.startsWith("image/") ? "sendPhoto" : "sendDocument", form);
  if (text.length > 1024) await sendText(text);
}

async function resolveChannel(message) {
  const chat = await message.getChat();
  if (!chat || (!chat.isChannel && !chat.channelMetadata)) return null;
  const inviteCode = chat.channelMetadata?.inviteCode;
  const channelName = inviteCode ? CHANNELS.get(inviteCode) : null;
  return channelName ? { chat, channelName } : null;
}

async function processMessage(message) {
  if (message.fromMe) return;
  const text = (message.body || "").trim();
  if (!shouldForward(text)) return;

  let source;
  try {
    source = await resolveChannel(message);
  } catch (error) {
    console.error("No se pudo identificar el canal:", error.message);
    return;
  }
  if (!source) return;

  const key = messageKey(message, source.channelName, text);
  if (seen.has(key) || inFlight.has(key)) return;
  inFlight.add(key);
  try {
    if (message.hasMedia) {
      try {
        const media = await message.downloadMedia();
        if (media) await sendMedia(media, text);
        else await sendText(text);
      } catch (error) {
        console.error(`No se pudo descargar multimedia de ${source.channelName}:`, error.message);
        await sendText(text);
      }
    } else {
      await sendText(text);
    }
    await remember(key);
    console.log(`REENVIADO: ${source.channelName}`);
  } catch (error) {
    console.error(`No se pudo reenviar una publicación de ${source.channelName}:`, error.message);
  } finally {
    inFlight.delete(key);
  }
}

async function main() {
  requireConfig();
  await loadSeen();

  const client = new Client({
    authStrategy: new LocalAuth({
      clientId: process.env.WHATSAPP_CLIENT_ID || "lxz-store-mediafire",
      dataPath: AUTH_PATH,
    }),
    puppeteer: {
      headless: process.env.WHATSAPP_HEADLESS !== "false",
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    },
  });

  client.on("qr", (qr) => {
    console.log("Escanea este QR con WhatsApp > Ajustes > Dispositivos vinculados:");
    qrcode.generate(qr, { small: true });
  });
  client.on("authenticated", () => console.log("WhatsApp autenticado."));
  client.on("ready", () => console.log(`Monitor activo para ${CHANNELS.size} canales. Filtro: MediaFire.`));
  client.on("auth_failure", (message) => console.error("Falló la autenticación de WhatsApp:", message));
  client.on("disconnected", (reason) => console.warn("WhatsApp desconectado:", reason));
  client.on("message_create", (message) => processMessage(message).catch((error) => console.error("Error procesando publicación:", error.message)));

  await client.initialize();
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { CHANNELS, chunks, shouldForward };
