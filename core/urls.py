from django.urls import path
from django.contrib.auth import views as auth_views
from .views import login_view, logout_view, dashboard, invitations, objects_page, notifications, users, visits, memos, laboratory, maintenance, deliveries, api_create_ticket, api_get_tickets, api_reply_ticket, api_get_memos, api_create_memo
from .monitoring import check_services_status
from .forms import EmailLoginForm

urlpatterns = [
    path("login/", login_view, name="login"),

    path("logout/", logout_view, name="logout"),

    path("dashboard/", dashboard, name="dashboard"),
    path("invitations/", invitations, name="invitations"),
    path("objects/", objects_page, name="objects"),
    path("notifications/", notifications, name="notifications"),
    path("users/", users, name="users"),
    path("visits/", visits, name="visits"),
    path("memos/", memos, name="memos"),
    path("laboratory/", laboratory, name="laboratory"),
    path("deliveries/", deliveries, name="deliveries"),
    path("maintenance/", maintenance, name="maintenance"),
    
    # API эндпоинты
    path("api/tickets/create/", api_create_ticket, name="api_create_ticket"),
    path("api/tickets/", api_get_tickets, name="api_get_tickets"),
    path("api/tickets/reply/", api_reply_ticket, name="api_reply_ticket"),
    path("api/memos/", api_get_memos, name="api_get_memos"),
    path("api/memos/create/", api_create_memo, name="api_create_memo"),
    path("api/check-services/", check_services_status, name="check_services_status"),
]
