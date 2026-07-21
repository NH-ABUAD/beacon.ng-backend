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
from rest_framework import serializers
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiResponse,
    OpenApiExample,
)
@extend_schema(
    tags=["Authentication"],
    summary="Register a new user",
    description="Creates a new Beacon user account.",
    request=RegisterSerializer,
    examples=[
        OpenApiExample(
            "Registration Example",
            value={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone_number": "08012345678",
                "password": "Password123!",
                "confirm_password": "Password123!"
            },
            request_only=True,
        )
    ],
    responses={
        201: RegisterSerializer,
        400: OpenApiResponse(description="Validation error")
    },
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

@extend_schema(
    tags=["Authentication"],
    summary="User Login",
    description="Authenticate a user and receive JWT access and refresh tokens.",
    request=CustomTokenObtainPairSerializer,
    examples=[
        OpenApiExample(
            "Admin Login",
            value={
                "email": "admin@beacon.com",
                "password": "Admin123!"
            },
            request_only=True,
        )
    ],
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=["Authentication"],
    summary="Forgot Password",
    description="Send a password reset OTP to the user's email.",
    request=ForgotPasswordSerializer,
    examples=[
        OpenApiExample(
            "Forgot Password",
            value={
                "email": "john@example.com"
            },
            request_only=True,
        )
    ],
    responses={
        200: OpenApiResponse(description="Verification code sent.")
    }
)
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


@extend_schema(
    tags=["Authentication"],
    summary="Verify OTP",
    description="Verify the password reset OTP.",
    request=VerifyOTPSerializer,
    examples=[
        OpenApiExample(
            "Verify OTP",
            value={
                "email": "john@example.com",
                "code": "123456"
            },
            request_only=True,
        )
    ],
    responses={
        200: OpenApiResponse(description="OTP verified.")
    }
)
class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'Code verified.'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    summary="Reset Password",
    description="Reset a user's password using a valid OTP.",
    request=ResetPasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password reset successful.")
    }
)
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


@extend_schema(
    summary="Current user profile",
    responses=UserProfileSerializer,
)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@extend_schema(
    summary="List users",
    responses=UserListSerializer(many=True),
)
class UserListView(generics.ListAPIView):
    queryset = User.objects.annotate(report_count=Count('reports')).order_by('-date_joined')
    serializer_class = UserListSerializer
    permission_classes = [IsAdminUser]


@extend_schema(
    tags=["Users"],
    summary="Suspend or Unsuspend User",
    description="Toggle a user's suspended status.",
    responses=inline_serializer(
        name="SuspendUserResponse",
        fields={
            "id": serializers.IntegerField(),
            "email": serializers.EmailField(),
            "is_suspended": serializers.BooleanField(),
        },
    ),
)
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


@extend_schema(
    tags=["Authentication"],
    summary="Logout",
    description="Invalidate a refresh token by adding it to the blacklist.",
    request=inline_serializer(
        name="LogoutRequest",
        fields={
            "refresh": serializers.CharField()
        },
    ),
    examples=[
        OpenApiExample(
            "Logout",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            request_only=True,
        )
    ],
    responses={
        200: OpenApiResponse(description="Logged out successfully."),
        400: OpenApiResponse(description="Invalid or missing refresh token.")
    }
)
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



@extend_schema(
    summary="Change password",
    request=ChangePasswordSerializer,
)
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
