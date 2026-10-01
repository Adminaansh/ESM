from rest_framework import serializers
from django.contrib.auth.models import User, Permission
from .models import Role, UserProfile,APIKey 

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id','name','prefix','created_at','is_active']
        read_only_fields = ['prefix','created_at']        

class UserProfileSerializer(serializers.ModelSerializer):
    role_name = serializers.ReadOnlyField(source='role.name')

    class Meta:
        model = UserProfile
        fields = ['role', 'role_name', 'employee_id', 'is_active']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        User = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=User, **profile_data)
        return User
