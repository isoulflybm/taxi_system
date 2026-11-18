from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile

User = get_user_model()


class PublicSignupForm(UserCreationForm):
    role = forms.ChoiceField(
        label="Я регистрируюсь как",
        choices=((UserProfile.Role.CUSTOMER, "Клиент"), (UserProfile.Role.DRIVER, "Водитель")),
    )
    phone = forms.CharField(label="Номер телефона", max_length=32)

    class Meta:
        model = User
        fields = ("username", "phone", "role")

    def clean_phone(self):
        phone = "".join(self.cleaned_data["phone"].split())
        if len("".join(char for char in phone if char.isdigit())) < 7:
            raise forms.ValidationError("Укажите корректный номер телефона.")
        if UserProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Этот номер телефона уже зарегистрирован.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": self.cleaned_data["role"], "phone": self.cleaned_data["phone"]},
            )
        return user
