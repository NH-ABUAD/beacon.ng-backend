from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EmergencyContact
from .models import PasswordResetOTP
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    emergency_contact_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(
        write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'password', 'phone_number', 'home_address',
                  'emergency_contact_name', 'emergency_contact_phone']

    def create(self, validated_data):
        contact_name = validated_data.pop('emergency_contact_name', None)
        contact_phone = validated_data.pop('emergency_contact_phone', None)

        user = User.objects.create_user(**validated_data)

        if contact_name and contact_phone:
            EmergencyContact.objects.create(
                user=user,
                name=contact_name,
                phone_number=contact_phone,
            )

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


class UserProfileSerializer(serializers.ModelSerializer):
    emergency_contacts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'phone_number', 'home_address',
            'is_staff', 'emergency_contacts',
        ]
        read_only_fields = ['id', 'email', 'is_staff']

    def get_emergency_contacts(self, obj):
        return [
            {'name': c.name, 'phone_number': c.phone_number,
                'relationship': c.relationship}
            for c in obj.emergency_contacts.all()
        ]


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'phone_number',
                  'is_staff', 'is_active', 'is_suspended', 'date_joined']


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'})
        return data
