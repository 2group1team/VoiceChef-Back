# 🍳 Voice Chef API

> REST API для мобильного приложения озвучки рецептов

**Версия:** 1.0.0 | **База:** `http://localhost:8000`

## 🚀 Быстрый старт

```bash
# Запуск
make up

# Регистрация
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Авторизация
curl -X POST "http://localhost:8000/auth/login" \
  -d "username=test@example.com&password=password123"

# Использование токена
curl -H "Authorization: Bearer <token>" "http://localhost:8000/users/me"
```

## 📋 API Endpoints

### 🔐 Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/auth/register` | Регистрация |
| `POST` | `/auth/login` | Авторизация |
| `POST` | `/auth/subscription/upgrade` | Активация премиума |

### 👤 Пользователи

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/users/me` | Профиль |
| `PUT` | `/users/me` | Обновить профиль |
| `POST` | `/users/me/change-password` | Сменить пароль |
| `GET` | `/users/me/limits` | Лимиты пользователя |

### 🍽 Блюда и рецепты

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/dishes` | Создать блюдо |
| `GET` | `/dishes` | Список блюд |
| `POST` | `/dishes/{id}/recipes` | Добавить рецепт |
| `GET` | `/dishes/{id}/recipes` | Рецепты блюда |
| `DELETE` | `/dishes/recipes/{id}` | Удалить рецепт |

### 🔍 Подбор рецептов

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/dishes/recipes/suggest` | Подбор по ингредиентам |
| `GET` | `/dishes/recipes/filter` | Фильтр по ингредиентам |

### ⭐ Избранное

| Метод | URL | Описание |
|-------|-----|----------|
| `PUT` | `/dishes/recipes/{id}/favorite` | Переключить избранное |
| `GET` | `/dishes/recipes/favorites` | Список избранных |

### 🖼 Медиа

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/dishes/recipes/{id}/photo` | Загрузить фото |
| `DELETE` | `/dishes/recipes/{id}/photo` | Удалить фото |

### 🔊 Озвучка

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/dishes/recipes/{id}/steps/{id}/tts` | Генерация TTS |
| `DELETE` | `/dishes/recipes/{id}/tts` | Удалить озвучку |

### 🥕 Ингредиенты

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/ingredients` | Список ингредиентов |
| `POST` | `/ingredients` | Добавить ингредиент |

### 📊 Отчеты

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/reports/stats` | Общая статистика |
| `GET` | `/reports/categories` | По категориям |
| `GET` | `/reports/popular_ingredients` | Популярные ингредиенты |

## 📝 Основные схемы

### Регистрация
```json
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "Имя",
  "last_name": "Фамилия"
}
```

### Создание блюда
```json
{
  "name": "Борщ",
  "category": "первое"  
}
```

### Создание рецепта
```json
{
  "cook_time": 90,
  "cook_method": "На плите",
  "servings": 4,
  "steps": [
    {"description": "Нарезать овощи", "duration": 15}
  ],
  "ingredients": [1, 2, 3]
}
```

### Подбор рецептов
```json
{
  "ingredients": ["картофель", "лук", "морковь"]
}
```

## 💎 Лимиты

| Функция | Бесплатно | Премиум |
|---------|-----------|---------|
| Блюда | 15 | 45 |
| Рецептов/блюдо | 3 | 5 |
| Размер фото | 2MB | 10MB |

## ⚠️ Коды ошибок

- `400` - Неверные данные
- `401` - Не авторизован
- `403` - Доступ запрещен / Лимит превышен
- `404` - Не найдено
- `409` - Конфликт (дубликат)
- `413` - Файл слишком большой
- `429` - Слишком много запросов

## 🔧 Примеры

### JavaScript
```javascript
class VoiceChefAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.token = null;
  }

  setToken(token) { this.token = token; }

  async request(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options, headers: { ...headers, ...options.headers }
    });
    return response.json();
  }

  async login(email, password) {
    const form = new FormData();
    form.append('username', email);
    form.append('password', password);
    const data = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST', body: form
    }).then(r => r.json());
    this.setToken(data.access_token);
    return data;
  }

  getDishes(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request(`/dishes?${params}`);
  }

  suggestRecipes(ingredients) {
    return this.request('/dishes/recipes/suggest', {
      method: 'POST', body: JSON.stringify({ ingredients })
    });
  }
}

// Использование
const api = new VoiceChefAPI();
await api.login('user@example.com', 'password123');
const dishes = await api.getDishes({ category: 'первое' });
```

### Python
```python
import requests

class VoiceChefClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, email, password):
        data = self.session.post(f"{self.base_url}/auth/login", 
                               data={'username': email, 'password': password}).json()
        self.session.headers.update({'Authorization': f"Bearer {data['access_token']}"})
        return data

    def get_dishes(self, **filters):
        return self.session.get(f"{self.base_url}/dishes", params=filters).json()

    def suggest_recipes(self, ingredients):
        return self.session.post(f"{self.base_url}/dishes/recipes/suggest",
                               json={'ingredients': ingredients}).json()

# Использование
client = VoiceChefClient()
client.login('user@example.com', 'password123')
dishes = client.get_dishes(category='первое')
```

## 🛠 Развертывание

### Docker
```bash
# Запуск
make up

# Проверка
curl http://localhost:8000/health
```

### Локально
```bash
# Установка
pip install -r requirements.txt

# БД
alembic upgrade head

# Запуск
uvicorn app.main:app --reload
```

## 📞 Поддержка

- **Docs:** http://localhost:8000/docs
- **Email:** support@voicechef.com
- **GitHub:** [Issues](https://github.com/voicechef/api/issues)

---

**© 2024 Voice Chef. Готовьте с удовольствием! 🍳**