from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Transaction, Budget, UserProfile, Category, EMI


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "email",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })


class TransactionForm(forms.ModelForm):

    class Meta:
        model = Transaction

        fields = (
            "title",
            "amount",
            "category",
            "transaction_type",
            "payment_method",
            "date",
            "note",
            "receipt_items",
            "receipt_number",
            "receipt_image",
        )

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Optional note...",
                    "class": "form-control"
                }
            ),
            "receipt_items": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Items detected from receipt (you can edit)",
                    "class": "form-control"
                }
            ),
            "receipt_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Invoice / bill / UPI reference (optional)"}),
            "receipt_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:
            self.fields["category"].queryset = Category.objects.filter(
                Q(owner=user) | Q(owner__isnull=True)
            )

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })


class BudgetForm(forms.ModelForm):

    class Meta:
        model = Budget

        fields = (
            "category",
            "month",
            "amount",
        )

        widgets = {
            "month": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            )
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:
            self.fields["category"].queryset = Category.objects.filter(
                Q(owner=user) | Q(owner__isnull=True)
            )

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })


class ProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile

        fields = (
            "monthly_income_target",
            "currency",
            "avatar",
        )

        widgets = {
            "monthly_income_target": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            )
        }
class EMIForm(forms.ModelForm):
    class Meta:
        model = EMI
        fields = ("lender", "loan_name", "principal", "annual_interest_rate", "tenure_months", "start_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "principal": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "annual_interest_rate": forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "form-control"}),
            "tenure_months": forms.NumberInput(attrs={"min": "1", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
