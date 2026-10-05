from rest_framework import serializers
from .models import User, UserInfo



class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "gender"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = [
            "user",
            "full_name",
            "user_information",
            "projects",
            "education",
            "skills",
            "hobbies",
            "contact_information",
        ]
        read_only_fields = ["user"]


class UserProfileSerializer(serializers.ModelSerializer):
    user_info = UserInfoSerializer(read_only=True)
    class Meta:
        model = User
        fields = [ "id", "email", "gender", "user_info"]




class UserContextSerializer(serializers.Serializer):
    personal_context = serializers.CharField(required=False, allow_blank=True, default="")
    past_projects = serializers.CharField(required=False, allow_blank=True, default="")
    resume = serializers.FileField(required=False, allow_null=True, default=None)

    class Meta:
        fields = ["personal_context", "past_projects", "resume"]