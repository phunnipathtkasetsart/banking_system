from django.shortcuts import redirect


def home(request):
    if not request.user.is_authenticated:
        return redirect("users:login")
    if request.user.is_bank_admin:
        return redirect("adminpanel:dashboard")
    return redirect("banking:dashboard")
