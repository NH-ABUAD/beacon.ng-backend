from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView, LoginView, ForgotPasswordView, VerifyOTPView, ResetPasswordView, MeView, UserListView, SuspendUserView, LogoutView, ChangePasswordView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login-refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('me/', MeView.as_view(), name='me'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/suspend/', SuspendUserView.as_view(), name='user-suspend'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
