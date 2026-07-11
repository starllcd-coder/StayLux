from django.urls import path

from sync_engine.views import (
    SyncApplyInboundView,
    SyncConfigView,
    SyncIngestView,
    SyncOutboxView,
    SyncPullView,
    SyncPushView,
    SyncQueueView,
    SyncRetryView,
    SyncStatusView,
)

app_name = "sync_engine"

urlpatterns = [
    path("status/", SyncStatusView.as_view(), name="status"),
    path("config/", SyncConfigView.as_view(), name="config"),
    path("push/", SyncPushView.as_view(), name="push"),
    path("pull/", SyncPullView.as_view(), name="pull"),
    path("retry/", SyncRetryView.as_view(), name="retry"),
    path("apply/", SyncApplyInboundView.as_view(), name="apply"),
    path("queue/", SyncQueueView.as_view(), name="queue"),
    path("events/outbox/", SyncOutboxView.as_view(), name="outbox"),
    path("events/ingest/", SyncIngestView.as_view(), name="ingest"),
]
