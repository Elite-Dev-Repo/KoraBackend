from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserInfo


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "gender", "is_staff", "is_superuser")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "gender")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "gender", "password1", "password2"),
            },
        ),
    )


@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name")
    search_fields = ("user__email", "full_name")
