import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def generate_unique_email():
    """Генерация уникального email для каждого теста"""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def generate_test_user():
    """Создание тестового пользователя с уникальными данными"""
    return {
        "email": generate_unique_email(),
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    }


class TestBasicAPI:
    """Базовые тесты API"""

    def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Voice Chef API" in data["message"]

    def test_docs_available(self):
        """Тест доступности документации"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """Тест схемы OpenAPI"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "info" in data
        assert "paths" in data


class TestAuthentication:
    """Тесты аутентификации"""

    def test_user_registration_success(self):
        """Тест успешной регистрации"""
        user_data = generate_test_user()

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert data["is_premium"] is False

    def test_user_registration_duplicate_email(self):
        """Тест регистрации с существующим email"""
        user_data = generate_test_user()

        # Первая регистрация
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 201

        # Попытка повторной регистрации с тем же email
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 409

    def test_user_login_success(self):
        """Тест успешной авторизации"""
        user_data = generate_test_user()

        # Регистрируем пользователя
        reg_response = client.post("/auth/register", json=user_data)
        assert reg_response.status_code == 201

        # Авторизуемся
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    def test_login_invalid_credentials(self):
        """Тест авторизации с неверными данными"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", data=login_data)

        assert response.status_code == 401

    def test_protected_endpoint_without_token(self):
        """Тест доступа к защищенному эндпоинту без токена"""
        response = client.get("/users/me")
        assert response.status_code == 401


class TestDishesBasic:
    """Базовые тесты блюд"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.user_data = generate_test_user()

        # Регистрируем пользователя
        reg_response = client.post("/auth/register", json=self.user_data)
        assert reg_response.status_code == 201

        # Получаем токен
        login_data = {
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_create_dish_success(self):
        """Тест создания блюда"""
        dish_data = {
            "name": f"Тестовое блюдо {uuid.uuid4().hex[:8]}",
            "category": "второе"
        }

        response = client.post("/dishes", json=dish_data, headers=self.headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == dish_data["name"]
        assert data["category"] == dish_data["category"]
        assert "id" in data

    def test_get_dishes_empty(self):
        """Тест получения пустого списка блюд"""
        response = client.get("/dishes", headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_dish_without_auth(self):
        """Тест создания блюда без авторизации"""
        dish_data = {
            "name": "Неавторизованное блюдо",
            "category": "второе"
        }

        response = client.post("/dishes", json=dish_data)
        assert response.status_code == 401


class TestIngredients:
    """Тесты ингредиентов"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.user_data = generate_test_user()

        # Регистрируем пользователя и получаем токен
        client.post("/auth/register", json=self.user_data)
        login_response = client.post("/auth/login", data={
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        })

        token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_get_ingredients_requires_auth(self):
        """Тест что получение ингредиентов требует авторизации"""
        response = client.get("/ingredients")
        assert response.status_code == 401

    def test_create_ingredient_success(self):
        """Тест создания ингредиента"""
        ingredient_data = {
            "name": f"тест_ингредиент_{uuid.uuid4().hex[:8]}",
            "type": "овощ"
        }

        response = client.post("/ingredients", json=ingredient_data, headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == ingredient_data["name"]
        assert data["type"] == ingredient_data["type"]


class TestUserProfile:
    """Тесты профиля пользователя"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.user_data = generate_test_user()

        # Регистрируем пользователя и получаем токен
        client.post("/auth/register", json=self.user_data)
        login_response = client.post("/auth/login", data={
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        })

        token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_get_current_user_profile(self):
        """Тест получения профиля текущего пользователя"""
        response = client.get("/users/me", headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == self.user_data["email"]
        assert "id" in data
        assert "is_premium" in data

    def test_get_user_limits(self):
        """Тест получения лимитов пользователя"""
        response = client.get("/users/me/limits", headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert "user_type" in data
        assert "limits" in data
        assert data["user_type"] == "free"  # По умолчанию бесплатный

    def test_premium_upgrade(self):
        """Тест активации премиум подписки"""
        response = client.post("/auth/subscription/upgrade", headers=self.headers)

        assert response.status_code == 200
        assert "активирована" in response.json()["message"]


class TestValidation:
    """Тесты валидации данных"""

    def test_registration_invalid_email(self):
        """Тест регистрации с невалидным email"""
        invalid_emails = [
            "invalid-email",
            "@invalid.com",
            "test@"
        ]

        for email in invalid_emails:
            user_data = {
                "email": email,
                "password": "ValidPass123!"
            }
            response = client.post("/auth/register", json=user_data)
            assert response.status_code == 422

    def test_registration_short_password(self):
        """Тест регистрации с коротким паролем"""
        user_data = {
            "email": generate_unique_email(),
            "password": "short"
        }
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 422

    def test_dish_empty_name(self):
        """Тест создания блюда с пустым названием"""
        # Сначала авторизуемся
        user_data = generate_test_user()
        client.post("/auth/register", json=user_data)
        login_response = client.post("/auth/login", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Пытаемся создать блюдо с пустым названием
        dish_data = {
            "name": "",
            "category": "второе"
        }
        response = client.post("/dishes", json=dish_data, headers=headers)
        assert response.status_code == 422


class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_nonexistent_endpoint(self):
        """Тест обращения к несуществующему эндпоинту"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Тест неподдерживаемого HTTP метода"""
        response = client.patch("/")  # PATCH не поддерживается для корня
        assert response.status_code == 405

    def test_malformed_json(self):
        """Тест отправки некорректного JSON"""
        headers = {"Content-Type": "application/json"}
        response = client.post("/auth/register",
                               data="invalid json",
                               headers=headers)
        assert response.status_code == 422