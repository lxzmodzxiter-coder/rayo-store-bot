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
    ADMIN_IDS: str = ""
    REFERRAL_BONUS: float = 0.0
    PAGE_SIZE: int = 6
    BROADCAST_DELAY: float = 0.05

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids(self) -> set[int]:
        result = set()
        for value in self.ADMIN_IDS.split(","):
            try:
                if value.strip():
                    result.add(int(value.strip()))
            except ValueError:
                continue
        result.add(self.OWNER_ID)
        return result


settings = Settings()
