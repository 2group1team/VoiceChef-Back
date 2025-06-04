# tests/conftest.py - Простая конфигурация без конфликтов
import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI тестовый клиент"""
    return TestClient(app)


@pytest.fixture
def unique_email():
    """Генерация уникального email для каждого теста"""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user_data(unique_email):
    """Базовые данные тестового пользователя"""
    return {
        "email": unique_email,
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def auth_headers(client, test_user_data):
    """Заголовки авторизации для тестов"""
    # Регистрируем пользователя
    reg_response = client.post("/auth/register", json=test_user_data)
    assert reg_response.status_code == 201

    # Получаем токен
    login_response = client.post("/auth/login", data={
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def premium_auth_headers(client, auth_headers):
    """Заголовки авторизации для премиум пользователя"""
    # Активируем премиум
    response = client.post("/auth/subscription/upgrade", headers=auth_headers)
    assert response.status_code == 200

    return auth_headers


def pytest_configure(config):
    """Конфигурация pytest"""
    # Отключаем warnings для чистого вывода
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)