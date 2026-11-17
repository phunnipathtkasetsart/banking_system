from django.contrib import admin

from .models import Account, Beneficiary, Transaction, TransactionEntry

admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(TransactionEntry)
admin.site.register(Beneficiary)
