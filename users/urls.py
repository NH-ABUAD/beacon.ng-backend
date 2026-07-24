from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from django.urls import include

from .views import (
    RegisterView, LoginView, ForgotPasswordView, VerifyOTPView, ResetPasswordView, EmergencyContactViewSet
)

router = DefaultRouter()
router.register(r'emergency-contacts', EmergencyContactViewSet,
                basename='emergency-contact')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login-refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('', include(router.urls)),
]
