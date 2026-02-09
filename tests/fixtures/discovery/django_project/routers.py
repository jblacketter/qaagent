"""Sample DRF router registration for testing route discovery."""
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("items", ItemViewSet)
router.register("users", UserViewSet)
