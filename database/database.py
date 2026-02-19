import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.logger import logger
from core.settings import settings


class DataBaseConnection:
    """
    Управление подключением к PostgreSQL с async поддержкой.

    Принципы:
    - Все параметры берутся из Settings (single source of truth)
    - Один engine и sessionmaker на приложение
    - Async context manager для безопасной работы с сессией
    """

    def __init__(self):  # , settings: Settings):
        self.engine = create_async_engine(
            settings.url(),
            echo=settings.ECHO,  # Логгирование SQL-запросов для отладки
            pool_pre_ping=settings.POOL_PRE_PING,  # Лечит «мертвые» коннекты (проверять соединение перед использованием (защита от dead connections))
            pool_size=settings.POOL_SIZE,  # Тюнинг пула по ситуации (сколько соединений держать в пуле)
            max_overflow=settings.MAX_OVERFLOW,  # Сколько дополнительных можно создать при пиках
            connect_args={
                'timeout': 10,  # Таймаут подключения (секунды)
                'command_timeout': 60,  # Таймаут выполнения команд (секунды)
                'server_settings': {
                    'application_name': 'bloom_app',
                },
            },
        )

        self.AsyncSessionLocal = async_sessionmaker(
            self.engine,  # Откуда брать соединения
            class_=AsyncSession,  # Указывает, какой класс сессии использовать, без этого параметра используется обычная Session
            expire_on_commit=False,  # Контролирует, что происходит с объектами после commit(). SQLAlchemy отслеживает объекты в памяти (Identity Map)
            autoflush=False,  # Контролирует, когда SQLAlchemy отправляет изменения в БД
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager для создания сессии БД.

        ⚠️ ВАЖНО: Коммит/откат управляются UnitOfWork, НЕ здесь!

        Эта функция ТОЛЬКО:
        - Создаёт async сессию из фабрики
        - Закрывает сессию после использования

        UnitOfWork сам решает: коммитить или откатывать.

        Использование:
            async with db.get_session() as session:
                # Передаём сессию в UnitOfWork
                uow = UnitOfWork(session)
                with uow:
                    await uow.users.create(...)
        """

        session = self.AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()

    async def connect(self) -> None:
        """Подключиться к БД (для lifespan startup) с retry логикой."""
        max_retries = 10
        retry_delay = 3  # секунды

        # Логируем параметры подключения (без пароля)
        db_url = settings.url()
        safe_url = (
            str(db_url).replace(str(db_url.password), '***')
            if db_url.password
            else str(db_url)
        )
        logger.info(f'[DATABASE] Попытка подключения к БД: {safe_url}')

        # Небольшая задержка перед первой попыткой (БД может еще инициализироваться)
        await asyncio.sleep(2)

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f'[DATABASE] Попытка подключения {attempt}/{max_retries}...'
                )
                # Проверяем соединение с БД
                async with self.engine.begin() as conn:
                    await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
                logger.info('[DATABASE] Успешно подключились к PostgreSQL')
                return
            except (TimeoutError, ConnectionError, OSError) as e:
                if attempt < max_retries:
                    logger.warning(
                        f'[DATABASE] Попытка подключения {attempt}/{max_retries} не удалась: {type(e).__name__}: {e}. '
                        f'Повтор через {retry_delay} сек...'
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(
                        retry_delay * 1.5, 10
                    )  # Экспоненциальная задержка, но не больше 10 сек
                else:
                    logger.error(
                        f'[DATABASE] Не удалось подключиться после {max_retries} попыток: {e}'
                    )
                    raise
            except Exception as e:
                # Для других ошибок тоже делаем retry
                if attempt < max_retries:
                    logger.warning(
                        f'[DATABASE] Попытка подключения {attempt}/{max_retries} не удалась: {type(e).__name__}: {e}. '
                        f'Повтор через {retry_delay} сек...'
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10)
                else:
                    logger.error(
                        f'[DATABASE] Не удалось подключиться после {max_retries} попыток: {e}'
                    )
                    raise

    async def is_connected(self) -> bool:
        """Проверить, подключена ли БД."""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
            return True
        except Exception as e:
            logger.warning(f'[DATABASE] Проверка соединения не удалась: {e}')
            return False

    async def dispose(self) -> None:
        """Корректно закрыть соединения пула (при завершении приложения)."""
        try:
            await self.engine.dispose()
            logger.info('[DATABASE] Пул соединений закрыт')
        except Exception as e:
            logger.error(f'[DATABASE] Ошибка при закрытии: {e}')
            raise


# Глобальный экземпляр
database = DataBaseConnection()
