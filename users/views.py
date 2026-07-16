# Create your views here.
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer
from .serializers import RegisterSerializer
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, PasswordResetOTP
from rest_framework.permissions import IsAdminUser
from .serializers import ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer, UserProfileSerializer, UserListSerializer, ChangePasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db.models import Count


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


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    queryset = User.objects.annotate(report_count=Count('reports')).order_by('-date_joined')
    serializer_class = UserListSerializer
    permission_classes = [IsAdminUser]


class SuspendUserView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        user.is_suspended = not user.is_suspended
        user.save()

        return Response({
            'id': user.id,
            'email': user.email,
            'is_suspended': user.is_suspended,
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        except (KeyError, TokenError):
            return Response({'detail': 'Invalid or missing refresh token.'}, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)
