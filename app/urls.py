from django.urls import path
from app.root.root_view import RootView
from app.login.login_view import LoginView
from app.register.register_view import RegisterView
from app.index.index_view import IndexView
from app.employee.employee_view import EmployeeView
from app.entry.entry_view import EntryView
from app.allocation.allocation_view import AllocationView

urlpatterns = [
    path('', RootView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('index/', IndexView.as_view(), name='index'),
    path('employee/', EmployeeView.as_view(), name='employee'),
    path('entry/', EntryView.as_view(), name='entry'),
    path('allocation/', AllocationView.as_view(), name='allocation'),
]
