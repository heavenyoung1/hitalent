from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # === PostgreSQL параметры ===
    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # SQLAlchemy параметры
    DRIVER: str = 'postgresql+asyncpg'
    ECHO: bool = False
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_PRE_PING: bool = True

    # === Драйвер для синхронного движка Alembic миграций. ===
    SYNC_DRIVER: str = 'postgresql'

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,  # В .env можно использовать как верхний, так и нижний регистр
    )

    def url(self) -> URL:
        """Собрать URL подключения безопасно (защита от SQL injection)."""
        return URL.create(
            drivername=self.DRIVER,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    def alembic_url(self) -> str:
        """Строка для подключения к БД ТОЛЬКО для выполнения Alembic миграций."""
        url = f'{self.SYNC_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
        return url


# Singleton - Единственный экземпляр настроек на всё приложение
settings = Settings()
