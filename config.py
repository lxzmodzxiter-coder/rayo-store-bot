from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    OWNER_ID: int
    DATABASE_URL: str
    REDIS_URL: str

    STORE_NAME: str = "LXZ STORE BEST"
    CURRENCY: str = "USD"
    TIMEZONE: str = "America/Lima"

    OFFICIAL_CHANNEL_URL: str = ""
    SUPPORT_USERNAME: str = ""

    YAPE_NUMBER: str = ""
    PLIN_NUMBER: str = ""

    BINANCE_USDT_ENABLED: bool = False
    BINANCE_USDT_ADDRESS: str = ""
    BINANCE_USDT_NETWORK: str = "TRC20"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def load_config() -> Settings:
    try:
        return Settings()
    except Exception as e:
        raise RuntimeError(f"Error crítico en la configuración de entorno. Detalles: {e}")

settings = load_config()
