import time

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from azimuth_aggregation.app.azimuth_endpoint import router


app = FastAPI(
    debug=True,
    # lifespan=lifespan,
    title="API",  # test2
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "DELETE",
        "PATCH",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)

app.include_router(router)

@app.get("/health", status_code=status.HTTP_200_OK)
def healthcheck():
    """
    проверка доступности сервиса
    :return:
    """
    return {"message": "Fastapi is running"}


if __name__ == "__main__":
    # локальный запуск
    # python backend/app/main.py
    import os
    import subprocess
    import sys

    cmd = [
        "granian",
        "--interface",
        "asgi",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--workers",
        "1",
        "--reload",
        "--access-log",
        "--access-log-fmt",
        '[%(time)s] %(addr)s - "%(method)s %(path)s" %(status)d',
        "main:app",
    ]

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        subprocess.run(cmd, check=True, env=env)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")  # noqa: RUF001
    except subprocess.CalledProcessError as e:
        print(f"Ошибка запуска Granian: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Ошибка: granian не найден. Убедитесь, что вы активировали виртуальное окружение и установили зависимости.",
            file=sys.stderr,
        )
        sys.exit(1)
