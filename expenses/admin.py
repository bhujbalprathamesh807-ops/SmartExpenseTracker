from django.contrib import admin
from .models import Category, Transaction, Budget, UserProfile, EMI, Payment

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(Budget)
admin.site.register(UserProfile)
admin.site.register(EMI)
admin.site.register(Payment)
