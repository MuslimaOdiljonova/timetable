from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from .forms import LoginForm

ROLE_REDIRECT = {
    'teacher': '/teacher/',
    'dekan':   '/dekan/',
    'admin':   '/admin/',
}

def get_redirect_url(user):
    return ROLE_REDIRECT.get(user.role, '/')


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(get_redirect_url(request.user))
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )

        if user is None:
            form.add_error(None, 'Invalid username/email or password.')
            return render(request, self.template_name, {'form': form})

        if not user.is_active:
            form.add_error(None, 'This account has been disabled.')
            return render(request, self.template_name, {'form': form})

        login(request, user)

        # Session expiry: browser close vs 2 weeks
        if not form.cleaned_data.get('remember_me'):
            request.session.set_expiry(0)          # expires on browser close
        else:
            request.session.set_expiry(1209600)    # 2 weeks in seconds

        # Honor ?next= param but only for safe internal URLs
        next_url = request.GET.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        return redirect(get_redirect_url(user))


class LogoutView(View):
    def get(self, request):   # allows link click
        logout(request)
        return redirect('accounts:login')

    def post(self, request):  # allows form submit
        logout(request)
        return redirect('accounts:login')


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        return render(request, self.template_name, {'user': request.user})