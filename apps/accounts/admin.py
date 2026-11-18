from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserProfile

User = get_user_model()


class TaxiProfileFieldsMixin:
    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            return ""
        existing = UserProfile.objects.filter(phone=phone)
        if self.instance.pk:
            existing = existing.exclude(user_id=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Этот номер телефона уже указан у другого пользователя.")
        return phone


class TaxiUserCreationForm(TaxiProfileFieldsMixin, UserCreationForm):
    role = forms.ChoiceField(
        label="Роль в Taxi KG",
        choices=UserProfile.Role.choices,
        initial=UserProfile.Role.CUSTOMER,
    )
    phone = forms.CharField(label="Телефон", max_length=32, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class TaxiUserChangeForm(TaxiProfileFieldsMixin, UserChangeForm):
    role = forms.ChoiceField(label="Роль в Taxi KG", choices=UserProfile.Role.choices)
    phone = forms.CharField(label="Телефон", max_length=32, required=False)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            default_role = UserProfile.Role.ADMIN if self.instance.is_staff else UserProfile.Role.CUSTOMER
            profile, _ = UserProfile.objects.get_or_create(
                user=self.instance,
                defaults={"role": default_role},
            )
            self.fields["role"].initial = profile.role
            self.fields["phone"].initial = profile.phone or ""


class TaxiUserAdmin(DjangoUserAdmin):
    add_form = TaxiUserCreationForm
    form = TaxiUserChangeForm
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "role", "phone"),
        }),
    )
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Профиль Taxi KG", {"fields": ("role", "phone")}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        UserProfile.objects.update_or_create(
            user=obj,
            defaults={
                "role": form.cleaned_data["role"],
                "phone": form.cleaned_data["phone"].strip() or None,
            },
        )


admin.site.unregister(User)
admin.site.register(User, TaxiUserAdmin)
