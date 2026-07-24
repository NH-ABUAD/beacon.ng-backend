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
    @staticmethod
    def get_role(user):
        if user.is_superuser:
            return 'Super Admin'
        if user.is_staff:
            return 'Admin'
        return 'Reporter'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['email'] = user.email
        token['role'] = cls.get_role(user)
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
            'role': self.get_role(self.user),
            'emergency_contacts': [
                {
                    'name': c.name,
                    'phone_number': c.phone_number,
                    'relationship': c.relationship,
                }
                for c in self.user.emergency_contacts.all()
            ],
        }

        if self.user.is_staff:
            from dashboard.models import SystemLog
            request = self.context.get('request')
            ip = request.META.get('REMOTE_ADDR') if request else None
            SystemLog.objects.create(
                admin=self.user,
                action=f'Admin session started — {self.user.email}',
                ip_address=ip,
            )

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
    role = serializers.SerializerMethodField()
    report_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'role', 'is_staff',
                  'is_active', 'is_suspended', 'date_joined', 'report_count']

    def get_role(self, obj):
        if obj.is_superuser:
            return 'Super Admin'
        if obj.is_staff:
            return 'Admin'
        return 'Reporter'


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


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'phone_number', 'relationship']
