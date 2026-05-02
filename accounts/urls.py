from django.urls import path, include
from .views import LoginView, LogoutView, ProfileView

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),

    # ONLY include timetable admin routes
    path('admin-panel/', include('timetable.urls.admin')),
]