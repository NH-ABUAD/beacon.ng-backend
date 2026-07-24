from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EmergencyContact
from .models import PasswordResetOTP
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'password',
                  'phone_number', 'home_address']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'phone_number': self.user.phone_number,
            'home_address': self.user.home_address,
            'is_staff': self.user.is_staff,
            'emergency_contacts': [
                {
                    'name': c.name,
                    'phone_number': c.phone_number,
                    'relationship': c.relationship,
                }
                for c in self.user.emergency_contacts.all()
            ],
        }
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "No account found with this email.")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
            otp = PasswordResetOTP.objects.filter(
                user=user, code=data['code']).latest('created_at')
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            raise serializers.ValidationError("Invalid code.")

        if not otp.is_valid():
            raise serializers.ValidationError(
                "Code has expired or already been used.")

        data['user'] = user
        data['otp'] = otp
        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."})

        try:
            user = User.objects.get(email=data['email'])
            otp = PasswordResetOTP.objects.filter(
                user=user, code=data['code']).latest('created_at')
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            raise serializers.ValidationError("Invalid code.")

        if not otp.is_valid():
            raise serializers.ValidationError(
                "Code has expired or already been used.")

        data['user'] = user
        data['otp'] = otp
        return data


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'phone_number', 'relationship']
