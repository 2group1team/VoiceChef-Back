from fastapi import APIRouter
from .auth import router as auth_router
from .dishes import router as dishes_router
from .recipes import router as recipes_router
from .ingredients import router as ingredients_router
from .favorites import router as favorites_router
from .suggestions import router as suggestions_router
from .media import router as media_router
from .tts import router as tts_router
from .reports import router as reports_router
from .admin import router as admin_router
from .analytics import router as analytics_router
from .users import router as users_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(dishes_router)
router.include_router(recipes_router)
router.include_router(ingredients_router)
router.include_router(favorites_router)
router.include_router(suggestions_router)
router.include_router(media_router)
router.include_router(tts_router)
router.include_router(reports_router)
router.include_router(admin_router)
router.include_router(analytics_router)
router.include_router(users_router)


__all__ = ['router']
