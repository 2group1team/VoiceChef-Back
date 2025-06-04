def get_user_limits(is_premium: bool) -> dict:
    """
    Возвращает лимиты для пользователя в зависимости от типа подписки
    """
    if is_premium:
        return {
            "max_dishes": 45,
            "max_recipes_per_dish": 5,
            "max_photo_size": 10 * 1024 * 1024,  # 10MB
            "max_tts_cache_size": 200 * 1024 * 1024,  # 200MB
            "can_use_premium_tts": True,
            "max_ingredients_per_recipe": 50,
            "can_export_recipes": True
        }
    else:
        return {
            "max_dishes": 15,
            "max_recipes_per_dish": 3,
            "max_photo_size": 2 * 1024 * 1024,  # 2MB
            "max_tts_cache_size": 50 * 1024 * 1024,  # 50MB
            "can_use_premium_tts": False,
            "max_ingredients_per_recipe": 20,
            "can_export_recipes": False
        }