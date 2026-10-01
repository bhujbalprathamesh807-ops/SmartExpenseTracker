from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("payment/", views.payment, name="payment"),
    path("payment/success/", views.payment_success, name="payment_success"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions/", views.transactions, name="transactions"),
    path("transactions/add/", views.add_transaction, name="add_transaction"),
    path("transactions/<int:pk>/edit/", views.edit_transaction, name="edit_transaction"),
    path("transactions/<int:pk>/delete/", views.delete_transaction, name="delete_transaction"),
    path("budgets/", views.budgets, name="budgets"),
    path("reports/", views.reports, name="reports"),
    path("emi/", views.emi_list, name="emi"),
    path("emi/<int:pk>/pay/", views.emi_pay, name="emi_pay"),
    path("profile/", views.profile, name="profile"),
    path("contact/", views.contact, name="contact"),
]
