from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from activity.services import log_activity
from core.utils import render_form

from .forms import ProfileForm, RegisterForm
from .services import register_customer


def register(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = register_customer(form, request)
        login(request, user)
        messages.success(request, "Account created. Welcome!")
        return redirect("banking:dashboard")
    return render_form(request, form, "Register", submit_label="Create account", back_url=reverse("users:login"))


class LoginView(auth_views.LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "core/form.html"
    success_url = reverse_lazy("users:profile")
    extra_context = {"title": "Change password", "submit_label": "Change password"}

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user.pk, "PASSWORD_CHANGE", username=self.request.user.username, request=self.request)
        messages.success(self.request, "Password changed.")
        return response


@login_required
def profile(request):
    return render(request, "users/profile.html", {"profile_user": request.user})


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request.user.pk, "PROFILE_UPDATE", username=request.user.username, request=request,
                     metadata={"changed": form.changed_data})
        messages.success(request, "Profile updated.")
        return redirect("users:profile")
    return render_form(request, form, "Edit profile", back_url=reverse("users:profile"))
