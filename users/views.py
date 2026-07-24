# Create your views here.
from rest_framework import generics, permissions, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer
from .serializers import RegisterSerializer
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .models import PasswordResetOTP, EmergencyContact
from .serializers import ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer, EmergencyContactSerializer
from drf_spectacular.utils import extend_schema


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])

        code = PasswordResetOTP.generate_code()
        PasswordResetOTP.objects.create(user=user, code=code)

        send_mail(
            subject='Your Beacon password reset code',
            message=f'Your verification code is: {code}\nThis code expires in 10 minutes.',
            from_email=None,
            recipient_list=[user.email],
        )
        return Response({'detail': 'Verification code sent.'}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'Code verified.'}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        otp = serializer.validated_data['otp']

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        otp.is_used = True
        otp.save()

        return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)


@extend_schema(tags=["User Profile"])
class EmergencyContactViewSet(viewsets.ModelViewSet):
    """
    Manage the authenticated user's emergency contacts.
    Always scoped to the current user — nobody can see or edit anyone else's.
    """
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
