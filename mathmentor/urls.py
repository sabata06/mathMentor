from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Router oluşturma
router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),  # Öğrenci endpoint’lerini ekle
]
