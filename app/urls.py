from django.urls import path
from app.root.root_view import RootView
from app.login.login_view import LoginView
from app.register.register_view import RegisterView
from app.index.index_view import IndexView
from app.employee.employee_view import EmployeeView
from app.entry.entry_view import EntryView
from app.allocation.allocation_view import AllocationView
from app.user.user_view import UserView
from app.vehicle.vehicle_view import VehicleView
from app.sanction.sanction_view import SanctionView
from app.events.events_view import EventsView
from app.access.access_view import AccessView
from app.detection.detection_views import (
    DetectorStreamView, DetectorControlView, EspaciosStatusView
)
from app.detection.plate_views import (
    PlateStreamView, PlateControlView, PlateStatusView,
    PlateStreamByIpView, PlateControlByIpView, PlateStatusByIpView,
    PlateLookupView, PlateLogAccessView
)

urlpatterns = [
    path('', RootView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('index/', IndexView.as_view(), name='index'),
    path('employee/', EmployeeView.as_view(), name='employee'),
    path('entry/', EntryView.as_view(), name='entry'),
    path('allocation/', AllocationView.as_view(), name='allocation'),
    path('user/', UserView.as_view(), name='user'),
    path('vehicle/', VehicleView.as_view(), name='vehicle'),
    path('sanction/', SanctionView.as_view(), name='sanction'),
    path('events/', EventsView.as_view(), name='events'),
    path('access/', AccessView.as_view(), name='access'),
    path('detection/stream/<int:area_id>/',
         DetectorStreamView.as_view(), name='detection_stream'),
    path('detection/control/<int:area_id>/',
         DetectorControlView.as_view(), name='detection_control'),
    path('detection/espacios/<int:area_id>/',
         EspaciosStatusView.as_view(), name='detection_espacios'),
    path('plates/stream/<int:device_id>/',
         PlateStreamView.as_view(), name='plates_stream'),
    path('plates/control/<int:device_id>/',
         PlateControlView.as_view(), name='plates_control'),
    path('plates/status/<int:device_id>/',
         PlateStatusView.as_view(), name='plates_status'),
    path('plates/stream_by_ip/',
         PlateStreamByIpView.as_view(), name='plates_stream_by_ip'),
    path('plates/control_by_ip/',
         PlateControlByIpView.as_view(), name='plates_control_by_ip'),
    path('plates/status_by_ip/',
         PlateStatusByIpView.as_view(), name='plates_status_by_ip'),
    path('plates/lookup/',
         PlateLookupView.as_view(), name='plates_lookup'),
    path('plates/log_access/',
         PlateLogAccessView.as_view(), name='plates_log_access'),
]
