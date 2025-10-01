from django.contrib import admin
from .models import Invitation, Memo, SentNotification, MaintenanceTicket, TicketReply, ServiceStatusLog

admin.site.register(Invitation)
admin.site.register(Memo)
admin.site.register(SentNotification)
admin.site.register(MaintenanceTicket)
admin.site.register(TicketReply)

@admin.register(ServiceStatusLog)
class ServiceStatusLogAdmin(admin.ModelAdmin):
    list_display = ("service_name", "is_working", "status_code", "checked_at")
    list_filter = ("service_name", "is_working")
    search_fields = ("service_name", "message", "url")
