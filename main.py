from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.logger import logger
from database.database import database
from presentation.department import router as department_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info('[STARTUP] Запуск приложения...')
    try:
        await database.connect()
        logger.info('[STARTUP] Приложение успешно запущено')
    except Exception as e:
        logger.error(f'[STARTUP] Ошибка при запуске: {e}')
        raise

    yield

    # Shutdown
    logger.info('[SHUTDOWN] Остановка приложения...')
    try:
        await database.dispose()
        logger.info('[SHUTDOWN] Приложение остановлено')
    except Exception as e:
        logger.error(f'[SHUTDOWN] Ошибка при остановке: {e}')


# Создание FastAPI приложения
app = FastAPI(
    title='HiTalent API',
    description='API для управления департаментами и сотрудниками',
    version='0.1.0',
    lifespan=lifespan,
)

# Подключение роутеров
app.include_router(department_router)


@app.get('/', tags=['health'])
async def root():
    """Health check endpoint."""
    return {
        'status': 'ok',
        'message': 'HiTalent API is running',
        'db_connected': await database.is_connected(),
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=8000,
        reload=True,
    )