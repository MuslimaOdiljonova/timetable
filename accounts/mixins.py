from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Usage in CBVs:
        class MyView(RoleRequiredMixin, TemplateView):
            allowed_roles = ['teacher']
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # super() handles the not-authenticated case via LoginRequiredMixin
        if not request.user.is_authenticated:
            return response
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return response


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['teacher']

class DekanRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['dekan']

class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['admin']