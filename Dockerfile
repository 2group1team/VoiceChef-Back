FROM python:3.11-slim

# Метаданные
LABEL maintainer="Voice Chef Team"
LABEL version="1.0.0"
LABEL description="Voice Chef API - приложение для озвучивания рецептов"

# Переменные окружения для оптимизации Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Создаем пользователя для безопасности
RUN groupadd -r voicechef && useradd -r -g voicechef voicechef

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    # Основные зависимости
    build-essential \
    libpq-dev \
    # Для health checks
    curl \
    # Для работы с аудио (TTS)
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    # Очистка кэша
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создаем рабочую директорию
WORKDIR /app

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаем необходимые директории
RUN mkdir -p /app/uploads/photos \
             /app/media \
             /app/cache \
             /app/logs \
             /app/static

# Копируем исходный код
COPY . .

# Устанавливаем права доступа
#RUN chown -R voicechef:voicechef /app

# Переключаемся на непривилегированного пользователя
#USER voicechef

# Порт приложения
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Команда запуска по умолчанию
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
