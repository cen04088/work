from django.conf import settings
from django.utils import timezone

def global_settings(request):
    context = {
        'settings': settings,
    }

    try:
        from core.models import PublicDataSyncState
        state = PublicDataSyncState.objects.filter(key="public_data_daily").first()
        if state and state.last_synced_at:
            context["public_data_synced_at"] = timezone.localtime(state.last_synced_at)
            context["public_data_sync_status"] = state.last_status
    except Exception:
        context["public_data_synced_at"] = None
        context["public_data_sync_status"] = ""

    return context
