from decimal import Decimal

from django import forms

from .models import Account, Beneficiary


def active_accounts(user):
    return Account.objects.filter(user=user, status=Account.Status.ACTIVE)


class AccountOpenForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("account_type", "nickname")


class AccountEditForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("nickname",)


class AdminAccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("account_type", "nickname", "status")


class AmountField(forms.DecimalField):
    def __init__(self, **kwargs):
        super().__init__(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), **kwargs)


class MoneyForm(forms.Form):
    """Customer deposit / withdraw."""

    account = forms.ModelChoiceField(queryset=Account.objects.none())
    amount = AmountField()
    description = forms.CharField(max_length=255, required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = active_accounts(user)


class TellerForm(forms.Form):
    """Admin deposit / withdraw on any account."""

    operation = forms.ChoiceField(choices=[("deposit", "Deposit"), ("withdraw", "Withdraw")])
    amount = AmountField()
    description = forms.CharField(max_length=255, required=False)


class TransferBaseForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=Account.objects.none())
    to_account_number = forms.CharField(max_length=10, min_length=10)
    amount = AmountField()
    description = forms.CharField(max_length=255, required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from_account"].queryset = active_accounts(user)


class TransferForm(TransferBaseForm):
    simulate_failure = forms.BooleanField(
        required=False,
        label="Simulate failure (demo)",
        help_text="Crash after debit/credit to prove the SQL transaction rolls back.",
    )


class DraftForm(TransferBaseForm):
    """Mongo `transfer_drafts` — same fields as a transfer, saved for later."""


class BeneficiaryCreateForm(forms.Form):
    account_number = forms.CharField(max_length=10, min_length=10)
    nickname = forms.CharField(max_length=50)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_account_number(self):
        number = self.cleaned_data["account_number"]
        account = Account.objects.filter(account_number=number).exclude(status=Account.Status.CLOSED).first()
        if account is None:
            raise forms.ValidationError("No open account with this number.")
        if account.user_id == self.user.pk:
            raise forms.ValidationError("That's your own account.")
        if Beneficiary.objects.filter(user=self.user, account=account).exists():
            raise forms.ValidationError("Already saved as a beneficiary.")
        self.account = account
        return number


class BeneficiaryEditForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ("nickname",)


class ReverseForm(forms.Form):
    reason = forms.CharField(max_length=200)
