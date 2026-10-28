from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings
import hashlib
import hmac
import json
import urllib.request
import urllib.error
import base64
from functools import wraps

from .forms import BudgetForm, EMIForm, ProfileForm, TransactionForm
from .models import Budget, Category, ContactMessage, EMI, Payment, Transaction, UserProfile

REGISTRATION_FEE = Decimal(getattr(settings, "REGISTRATION_FEE", "99.00"))
RAZORPAY_KEY_ID = getattr(settings, "RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = getattr(settings, "RAZORPAY_KEY_SECRET", "")
PAYMENT_DEMO_MODE = getattr(settings, "PAYMENT_DEMO_MODE", False)


def seed_categories(user):
    defaults = [
        ("Food", "🍔", "#f97316", "expense"),
        ("Transport", "🚗", "#0ea5e9", "expense"),
        ("Shopping", "🛍️", "#ec4899", "expense"),
        ("Bills", "💡", "#8b5cf6", "expense"),
        ("Health", "❤️", "#ef4444", "expense"),
        ("Entertainment", "🎬", "#14b8a6", "expense"),
        ("Education", "📚", "#6366f1", "expense"),
        ("Salary", "💼", "#22c55e", "income"),
        ("Other", "✨", "#64748b", "expense"),
    ]
    for name, icon, color, kind in defaults:
        Category.objects.get_or_create(
            name=name,
            owner=user,
            defaults={"icon": icon, "color": color, "kind": kind},
        )


TRIAL_DAYS = 30

def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def trial_ends_at(profile):
    return profile.trial_started_at + timedelta(days=TRIAL_DAYS)

def trial_active(profile):
    return not profile.subscription_active and timezone.now() < trial_ends_at(profile)

def has_access(user):
    if not user.is_authenticated:
        return False
    profile = get_profile(user)
    return profile.subscription_active or trial_active(profile)

def premium_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        profile = get_profile(request.user)
        if profile.subscription_active or trial_active(profile):
            return view_func(request, *args, **kwargs)
        messages.warning(request, "Your 30-day free trial has ended. Please complete the ₹99 Premium payment to continue.")
        return redirect("payment")
    return wrapper


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html", {"registration_fee": REGISTRATION_FEE, "trial_days": TRIAL_DAYS})


def _razorpay_order(amount, receipt):
    """Create a Razorpay order using the REST API (no SDK required)."""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return None, "Razorpay keys are not configured."
    payload = json.dumps({
        "amount": int((amount * 100).quantize(Decimal("1"))),
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    }).encode("utf-8")
    token = base64.b64encode(f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode()).decode()
    req = urllib.request.Request(
        "https://api.razorpay.com/v1/orders",
        data=payload,
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode()), None
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        return None, str(exc)


def payment(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first. Your 30-day free trial comes before Premium payment.")
        return redirect("login")
    profile = get_profile(request.user)
    if profile.subscription_active or trial_active(profile):
        return redirect("dashboard")

    next_page = "dashboard"
    if next_page not in {"login", "register"}:
        next_page = "login"
    request.session["payment_next"] = next_page

    order = None
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        receipt = f"SET-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
        order, error = _razorpay_order(REGISTRATION_FEE, receipt)
        if order:
            Payment.objects.create(order_id=order["id"], amount=REGISTRATION_FEE, status="created", purpose="access")
            request.session["razorpay_order_id"] = order["id"]
        else:
            messages.error(request, "Payment gateway is temporarily unavailable. Please try again.")

    return render(request, "payment.html", {
        "registration_fee": REGISTRATION_FEE,
        "upi_id": "bhujbalprathamesh807@oksbi",
        "upi_name": "Prathamesh Bhujbal",
        "payment_next": next_page,
        "trial_days": TRIAL_DAYS,
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "razorpay_order": order,
        "payment_demo_mode": PAYMENT_DEMO_MODE,
    })


def payment_success(request):
    if request.method != "POST":
        return redirect("payment")
    if not request.user.is_authenticated:
        messages.error(request, "Please log in before completing Premium payment.")
        return redirect("login")

    next_page = "dashboard"

    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_order_id = request.POST.get("razorpay_order_id", "")
    razorpay_signature = request.POST.get("razorpay_signature", "")
    verified = False

    if razorpay_payment_id and razorpay_order_id and razorpay_signature and RAZORPAY_KEY_SECRET:
        expected = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        verified = hmac.compare_digest(expected, razorpay_signature)
        if verified:
            Payment.objects.filter(order_id=razorpay_order_id, status="created").update(
                payment_id=razorpay_payment_id, signature=razorpay_signature,
                status="paid", paid_at=timezone.now()
            )

    if not verified and PAYMENT_DEMO_MODE:
        # Development-only escape hatch. Never enable this in production.
        order_id = request.session.get("razorpay_order_id") or f"DEMO-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
        payment_record, _ = Payment.objects.get_or_create(
            order_id=order_id, defaults={"amount": REGISTRATION_FEE, "purpose": "demo_access"}
        )
        payment_record.status = "paid"
        payment_record.paid_at = timezone.now()
        payment_record.save(update_fields=["status", "paid_at"])
        verified = True

    if not verified:
        messages.error(request, "Payment could not be verified. Please complete the ₹99 payment through the payment window.")
        return redirect("payment")

    payment_record = Payment.objects.filter(
        order_id=razorpay_order_id or request.session.get("razorpay_order_id"), status="paid"
    ).first()
    profile = get_profile(request.user)
    profile.subscription_active = True
    profile.save(update_fields=["subscription_active"])
    if payment_record:
        payment_record.user = request.user
        payment_record.save(update_fields=["user"])
    request.session["payment_completed"] = True
    request.session["payment_amount"] = str(REGISTRATION_FEE)
    if payment_record:
        request.session["paid_payment_record_id"] = payment_record.id
    request.session.pop("payment_next", None)
    request.session.pop("razorpay_order_id", None)
    messages.success(request, "₹99 payment verified. Continue to your account.")
    return redirect(next_page)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if not username or not email or not password or not confirm:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "registration/register.html")
        if len(password) < 6:
            messages.error(request, "Password must contain at least 6 characters.")
            return render(request, "registration/register.html")
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "registration/register.html")
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists. Please choose another username.")
            return render(request, "registration/register.html")
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "registration/register.html")

        try:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name)
            seed_categories(user)
            UserProfile.objects.create(user=user, subscription_active=False, trial_started_at=timezone.now())
        except IntegrityError:
            messages.error(request, "Could not create the account. Please try another username.")
            return render(request, "registration/register.html")

        login(request, user)
        messages.success(request, "Account created successfully. Your 30-day free trial has started!")
        return redirect("dashboard")

    return render(request, "registration/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile_obj, _ = UserProfile.objects.get_or_create(user=user, defaults={"trial_started_at": timezone.now()})
            login(request, user)
            if profile_obj.subscription_active or trial_active(profile_obj):
                messages.success(request, "Login successful. Welcome back!")
                return redirect(request.GET.get("next") if request.GET.get("next", "").startswith("/") else "dashboard")
            messages.warning(request, "Your 30-day free trial has ended. Complete the ₹99 Premium payment to open your dashboard.")
            return redirect("payment")
        messages.error(request, "Invalid username or password.")
    return render(request, "registration/login.html")


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("home")


@premium_required
def dashboard(request):
    seed_categories(request.user)
    today = timezone.localdate()
    start = today.replace(day=1)
    month_tx = Transaction.objects.filter(user=request.user, date__gte=start, date__lte=today)
    income = month_tx.filter(transaction_type="income").aggregate(v=Sum("amount"))["v"] or Decimal("0")
    expense = month_tx.filter(transaction_type="expense").aggregate(v=Sum("amount"))["v"] or Decimal("0")
    categories = Category.objects.filter(owner=request.user, kind="expense")
    cat_rows = []
    for category in categories:
        total = month_tx.filter(category=category, transaction_type="expense").aggregate(v=Sum("amount"))["v"] or Decimal("0")
        if total:
            cat_rows.append({"name": category.name, "value": float(total), "icon": category.icon, "color": category.color})
    cat_rows.sort(key=lambda x: x["value"], reverse=True)
    profile = get_profile(request.user)
    days_left = max((trial_ends_at(profile).date() - today).days, 0) if not profile.subscription_active else 0
    return render(request, "dashboard.html", {
        "income": income, "expense": expense, "balance": income - expense,
        "trial_active": trial_active(profile), "trial_days_left": days_left, "premium_active": profile.subscription_active,
        "recent": Transaction.objects.filter(user=request.user)[:6],
        "cat_rows": cat_rows[:6],
        "budget_total": Budget.objects.filter(user=request.user, month=start).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "month_name": today.strftime("%B %Y"),
        "emi_count": EMI.objects.filter(user=request.user).count(),
    })


@premium_required
def transactions(request):
    qs = Transaction.objects.filter(user=request.user)
    q = request.GET.get("q", "").strip()
    typ = request.GET.get("type", "")
    category = request.GET.get("category", "")
    if q:
        qs = qs.filter(title__icontains=q)
    if typ in {"income", "expense"}:
        qs = qs.filter(transaction_type=typ)
    if category.isdigit():
        qs = qs.filter(category_id=category)
    return render(request, "transactions.html", {
        "transactions": qs.order_by("-date", "-id"),
        "categories": Category.objects.filter(owner=request.user),
        "q": q, "typ": typ, "category": category,
    })


@premium_required
def add_transaction(request):
    seed_categories(request.user)
    form = TransactionForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, "Transaction added successfully.")
        return redirect("transactions")
    return render(request, "transaction_form.html", {"form": form, "title": "Add Transaction"})


@premium_required
def edit_transaction(request, pk):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user)
    form = TransactionForm(request.POST or None, request.FILES or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Transaction updated successfully.")
        return redirect("transactions")
    return render(request, "transaction_form.html", {"form": form, "title": "Edit Transaction", "scanner": False})


@premium_required
def delete_transaction(request, pk):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Transaction deleted successfully.")
    return redirect("transactions")


@premium_required
def budgets(request):
    month = timezone.localdate().replace(day=1)
    form = BudgetForm(request.POST or None, user=request.user, initial={"month": month})
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.month = month
        obj.save()
        messages.success(request, "Budget saved successfully.")
        return redirect("budgets")
    data = []
    for budget in Budget.objects.filter(user=request.user, month=month):
        spent = Transaction.objects.filter(user=request.user, category=budget.category, transaction_type="expense", date__year=month.year, date__month=month.month).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        pct = min(100, float(spent / budget.amount * 100)) if budget.amount else 0
        data.append({"budget": budget, "spent": spent, "pct": pct, "remaining": budget.amount - spent})
    return render(request, "budgets.html", {"items": data, "form": form})


@premium_required
def reports(request):
    today = timezone.localdate()
    rows = []
    for category in Category.objects.filter(owner=request.user, kind="expense"):
        total = Transaction.objects.filter(user=request.user, category=category, transaction_type="expense", date__year=today.year).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        if total:
            rows.append({"name": category.name, "value": float(total), "icon": category.icon})
    monthly = []
    for i in range(5, -1, -1):
        y = today.year + (today.month - i - 1) // 12
        m = (today.month - i - 1) % 12 + 1
        total = Transaction.objects.filter(user=request.user, transaction_type="expense", date__year=y, date__month=m).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        monthly.append({"label": date(y, m, 1).strftime("%b"), "value": float(total)})
    return render(request, "reports.html", {"rows": rows, "monthly": monthly})


@premium_required
def emi_list(request):
    form = EMIForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        principal = Decimal(obj.principal)
        annual = Decimal(obj.annual_interest_rate)
        n = int(obj.tenure_months)
        if principal <= 0 or n <= 0 or annual < 0:
            form.add_error(None, "Enter a principal greater than 0, a positive tenure, and a non-negative interest rate.")
            emis = EMI.objects.filter(user=request.user)
            return render(request, "emi.html", {"form": form, "emis": emis})
        monthly_rate = annual / Decimal("1200")
        if monthly_rate == 0:
            emi = principal / Decimal(n)
        else:
            factor = (Decimal(1) + monthly_rate) ** n
            emi = principal * monthly_rate * factor / (factor - Decimal(1))
        emi = emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = (emi * n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        obj.monthly_emi = emi
        obj.total_payable = total
        obj.total_interest = max(total - principal, Decimal("0"))
        obj.save()
        messages.success(request, f"EMI created. Monthly EMI: ₹{emi:,.2f}")
        return redirect("emi")
    emis = EMI.objects.filter(user=request.user)
    return render(request, "emi.html", {"form": form, "emis": emis})


@premium_required
def emi_pay(request, pk):
    emi = get_object_or_404(EMI, pk=pk, user=request.user)
    if request.method == "POST" and emi.paid_installments < emi.tenure_months:
        seed_categories(request.user)
        category = Category.objects.get(owner=request.user, name="Other")
        Transaction.objects.create(
            user=request.user,
            title=f"EMI - {emi.loan_name}",
            amount=emi.monthly_emi,
            category=category,
            transaction_type="expense",
            payment_method="Bank",
            date=timezone.localdate(),
            note=f"EMI installment {emi.paid_installments + 1} of {emi.tenure_months}",
        )
        emi.paid_installments += 1
        emi.save(update_fields=["paid_installments"])
        messages.success(request, "EMI installment recorded and added to Transactions.")
    return redirect("emi")


@premium_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")
    return render(request, "profile.html", {"form": form, "profile": profile_obj})


def contact(request):
    if request.method == "POST":
        data = {k: request.POST.get(k, "").strip() for k in ("name", "email", "subject", "message")}
        if not all(data.values()):
            messages.error(request, "Please fill in all fields.")
        else:
            ContactMessage.objects.create(**data)
            messages.success(request, "Your message has been sent successfully!")
            return redirect("contact")
    return render(request, "contact.html")
