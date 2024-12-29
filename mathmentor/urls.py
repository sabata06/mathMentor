from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet,AssignmentViewSet

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Router oluşturma
router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'assignments', AssignmentViewSet, basename='assignment')  # Ödev endpoint'i

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),  # Öğrenci endpoint’lerini ekle
]
