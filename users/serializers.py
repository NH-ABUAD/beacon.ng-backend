from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
    
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Extra data embedded inside the token itself
        token['is_staff'] = user.is_staff
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Extra data returned alongside access/refresh in the response body
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'is_staff': self.user.is_staff,
        }
        return data