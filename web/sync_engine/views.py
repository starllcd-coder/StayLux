from __future__ import annotations

import os

from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from sync_engine.models import SyncConfig, SyncEvent, SyncInboundEvent, SyncEventStatus
from sync_engine.serializers import InboundSyncSerializer, SyncConfigSerializer, SyncEventSerializer
from sync_engine.services import (
    apply_inbound_events,
    get_or_create_sync_config,
    list_outbox_events,
    pull_remote_events,
    push_pending_events,
    reset_failed_events_for_retry,
    retry_dead_letters,
)


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        staff = getattr(request.user, "staff_profile", None)
        if not staff:
            return False
        return staff.role in {"owner_admin", "manager"}


class SyncStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cfg = get_or_create_sync_config()
        agg = SyncEvent.objects.aggregate(
            pending=Count("id", filter=Q(status=SyncEventStatus.PENDING)),
            failed=Count("id", filter=Q(status=SyncEventStatus.FAILED)),
            synced=Count("id", filter=Q(status=SyncEventStatus.SYNCED)),
            dead_letter=Count("id", filter=Q(is_dead_letter=True)),
        )
        return Response(
            {
                "config": SyncConfigSerializer(cfg).data,
                "queue": agg,
                "inbound_unprocessed": SyncInboundEvent.objects.filter(is_processed=False).count(),
            },
            status=status.HTTP_200_OK,
        )


class SyncConfigView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        cfg = get_or_create_sync_config()
        return Response(SyncConfigSerializer(cfg).data, status=status.HTTP_200_OK)

    def patch(self, request):
        cfg = get_or_create_sync_config()
        serializer = SyncConfigSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class SyncPushView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        limit = request.data.get("limit") or 200
        try:
            limit = int(limit)
        except Exception:
            limit = 200
        summary = push_pending_events(limit=max(1, min(limit, 1000)))
        return Response(summary, status=status.HTTP_200_OK)


class SyncPullView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        limit = request.data.get("limit") or 200
        try:
            limit = int(limit)
        except Exception:
            limit = 200
        summary = pull_remote_events(limit=max(1, min(limit, 1000)))
        return Response(summary, status=status.HTTP_200_OK)


class SyncApplyInboundView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        limit = request.data.get("limit") or 200
        try:
            limit = int(limit)
        except Exception:
            limit = 200
        summary = apply_inbound_events(limit=max(1, min(limit, 3000)))
        return Response(summary, status=status.HTTP_200_OK)


class SyncRetryView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request):
        retry_failed_limit = request.data.get("retry_failed_limit") or 1000
        retry_dead_limit = request.data.get("retry_dead_limit") or 200
        try:
            retry_failed_limit = int(retry_failed_limit)
        except Exception:
            retry_failed_limit = 1000
        try:
            retry_dead_limit = int(retry_dead_limit)
        except Exception:
            retry_dead_limit = 200
        reset_count = reset_failed_events_for_retry(limit=max(1, min(retry_failed_limit, 10000)))
        dead_count = retry_dead_letters(limit=max(1, min(retry_dead_limit, 1000)))
        return Response(
            {"retry_failed_reset": reset_count, "dead_letters_requeued": dead_count},
            status=status.HTTP_200_OK,
        )


class SyncQueueView(APIView):
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        limit = request.query_params.get("limit") or 100
        try:
            limit = int(limit)
        except Exception:
            limit = 100
        limit = max(1, min(limit, 500))
        events = SyncEvent.objects.order_by("-created_at")[:limit]
        return Response(SyncEventSerializer(events, many=True).data, status=status.HTTP_200_OK)


class SyncIngestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cfg = SyncConfig.objects.filter(id=1).first()
        expected_secret = ""
        if cfg and cfg.shared_secret:
            expected_secret = cfg.shared_secret
        else:
            expected_secret = os.environ.get("STAYLUX_SYNC_SHARED_SECRET", "")
        if expected_secret:
            incoming = request.headers.get("X-Sync-Secret", "")
            if incoming != expected_secret:
                return Response({"detail": "Invalid sync secret."}, status=status.HTTP_403_FORBIDDEN)

        serializer = InboundSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source_node = serializer.validated_data.get("source_node", "")
        accepted = []
        for event in serializer.validated_data["events"]:
            event_uuid = event.get("event_uuid")
            if not event_uuid:
                continue
            _, created = SyncInboundEvent.objects.get_or_create(
                event_uuid=event_uuid,
                source_node=source_node,
                defaults={"payload": event},
            )
            if created:
                accepted.append(str(event_uuid))

        return Response(
            {
                "accepted_event_uuids": accepted,
                "accepted_count": len(accepted),
            },
            status=status.HTTP_200_OK,
        )


class SyncOutboxView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cfg = SyncConfig.objects.filter(id=1).first()
        expected_secret = ""
        if cfg and cfg.shared_secret:
            expected_secret = cfg.shared_secret
        else:
            expected_secret = os.environ.get("STAYLUX_SYNC_SHARED_SECRET", "")
        if expected_secret:
            incoming = request.headers.get("X-Sync-Secret", "")
            if incoming != expected_secret:
                return Response({"detail": "Invalid sync secret."}, status=status.HTTP_403_FORBIDDEN)

        limit = request.query_params.get("limit") or 200
        since_raw = (request.query_params.get("since") or "").strip()
        exclude_source_node = (request.query_params.get("exclude_source_node") or "").strip()
        try:
            limit = int(limit)
        except Exception:
            limit = 200
        since_dt = None
        if since_raw:
            from django.utils.dateparse import parse_datetime

            since_dt = parse_datetime(since_raw)

        events = list_outbox_events(limit=max(1, min(limit, 1000)), since=since_dt, exclude_source_node=exclude_source_node)
        return Response({"events": events, "count": len(events)}, status=status.HTTP_200_OK)
