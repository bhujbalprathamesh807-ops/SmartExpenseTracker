from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    CATEGORY_TYPES = [("expense", "Expense"), ("income", "Income")]
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=10, default="💰")
    kind = models.CharField(max_length=10, choices=CATEGORY_TYPES, default="expense")
    color = models.CharField(max_length=20, default="#6366f1")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Transaction(models.Model):
    PAYMENT_CHOICES = [
        ("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card"), ("Bank", "Bank"), ("Other", "Other")
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=10, choices=[("expense","Expense"),("income","Income")])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="UPI")
    date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True)
    receipt_items = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=120, blank=True)
    receipt_image = models.ImageField(upload_to="receipts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category", "month")
        ordering = ["-month"]

    def __str__(self):
        return f"{self.category} - ₹{self.amount}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    monthly_income_target = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    currency = models.CharField(max_length=10, default="INR")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    subscription_active = models.BooleanField(default=False)
    trial_started_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username

class ContactMessage(models.Model):

    name = models.CharField(max_length=100)

    email = models.EmailField()

    subject = models.CharField(max_length=100)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"
class EMI(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emis")
    lender = models.CharField(max_length=120)
    loan_name = models.CharField(max_length=150)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    annual_interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tenure_months = models.PositiveIntegerField()
    start_date = models.DateField(default=timezone.localdate)
    monthly_emi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_installments = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def remaining_installments(self):
        return max(self.tenure_months - self.paid_installments, 0)

    @property
    def remaining_amount(self):
        return (self.monthly_emi * self.remaining_installments).quantize(Decimal('0.01'))

    @property
    def outstanding_principal(self):
        from decimal import Decimal, ROUND_HALF_UP
        if self.remaining_installments <= 0:
            return Decimal("0.00")
        principal = Decimal(self.principal)
        n = int(self.tenure_months)
        paid = min(int(self.paid_installments), n)
        r = Decimal(self.annual_interest_rate) / Decimal("1200")
        if r == 0:
            balance = principal * Decimal(self.remaining_installments) / Decimal(n)
        else:
            factor = (Decimal("1") + r) ** paid
            balance = principal * factor - Decimal(self.monthly_emi) * (factor - Decimal("1")) / r
        return max(balance, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def remaining_interest(self):
        from decimal import Decimal, ROUND_HALF_UP
        value = max(Decimal("0"), Decimal(self.remaining_amount) - Decimal(self.outstanding_principal))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return f"{self.loan_name} - ₹{self.monthly_emi}"


class Payment(models.Model):
    STATUS_CHOICES = [("created", "Created"), ("paid", "Paid"), ("failed", "Failed")]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    order_id = models.CharField(max_length=80, unique=True)
    payment_id = models.CharField(max_length=80, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("99.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    purpose = models.CharField(max_length=50, default="access")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_id} - ₹{self.amount} - {self.status}"
