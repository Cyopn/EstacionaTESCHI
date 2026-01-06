from django.urls import path
from app.root.root_view import RootView
from app.login.login_view import LoginView
from app.register.register_view import RegisterView

urlpatterns = [
    path('', RootView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
]
