from __future__ import annotations

import json
import os
import socket
import threading
from datetime import timedelta
from typing import Any
from urllib import error, parse, request

from django.apps import apps
from django.db.models import Q
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from sync_engine.models import SyncConfig, SyncEvent, SyncEventStatus, SyncInboundEvent


SYNC_MODEL_LABELS = {
    "settings_app.propertyprofile",
    "inventory.unit",
    "guests.guest",
    "bookings.booking",
    "billing.invoice",
    "billing.payment",
    "maintenance.maintenancerequest",
    "housekeeping.housekeepingtask",
}


def get_or_create_sync_config() -> SyncConfig:
    defaults = {
        "node_id": os.environ.get("STAYLUX_NODE_ID", socket.gethostname()),
        "enabled": os.environ.get("STAYLUX_SYNC_ENABLED", "1") == "1",
        "mode": os.environ.get("STAYLUX_SYNC_MODE", "auto"),
        "remote_base_url": os.environ.get("STAYLUX_SYNC_REMOTE_URL", ""),
        "api_token": os.environ.get("STAYLUX_SYNC_API_TOKEN", ""),
        "shared_secret": os.environ.get("STAYLUX_SYNC_SHARED_SECRET", ""),
        "interval_seconds": int(os.environ.get("STAYLUX_SYNC_INTERVAL", "30")),
        "max_retry_attempts": int(os.environ.get("STAYLUX_SYNC_MAX_RETRY", "8")),
        "conflict_policy": os.environ.get("STAYLUX_SYNC_CONFLICT_POLICY", "last_write_wins"),
    }
    cfg, _ = SyncConfig.objects.get_or_create(id=1, defaults=defaults)
    return cfg


def should_capture_model(model_label: str) -> bool:
    return model_label in SYNC_MODEL_LABELS


def serialize_instance(instance) -> dict[str, Any]:
    data = model_to_dict(instance)
    data["id"] = instance.pk
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            try:
                data[key] = value.isoformat()
            except Exception:
                data[key] = str(value)
    return data


def record_sync_event(*, instance, operation: str, payload: dict[str, Any] | None = None) -> None:
    model_label = instance._meta.label_lower
    if not should_capture_model(model_label):
        return

    try:
        cfg = get_or_create_sync_config()
        SyncEvent.objects.create(
            source_node=cfg.node_id or "",
            model_label=model_label,
            object_pk=str(instance.pk),
            operation=operation,
            payload=payload or serialize_instance(instance),
        )
    except Exception:
        return


def _is_online_mode(cfg: SyncConfig) -> bool:
    if not cfg.enabled:
        return False
    if cfg.mode == "offline":
        return False
    if cfg.mode in {"online", "auto"}:
        return True
    return False


def _request_with_auth(cfg: SyncConfig, url: str, method: str = "GET", data: dict[str, Any] | None = None):
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if cfg.api_token:
        req.add_header("Authorization", f"Bearer {cfg.api_token}")
    if cfg.shared_secret:
        req.add_header("X-Sync-Secret", cfg.shared_secret)
    return req


def _mark_event_failed(event: SyncEvent, error_message: str, cfg: SyncConfig) -> None:
    event.attempts += 1
    event.last_attempt_at = timezone.now()
    event.last_error = error_message
    max_attempts = max(cfg.max_retry_attempts or 8, 1)
    if event.attempts >= max_attempts:
        event.is_dead_letter = True
        event.status = SyncEventStatus.FAILED
        event.next_retry_at = None
    else:
        wait_seconds = min(30 * (2 ** max(event.attempts - 1, 0)), 3600)
        event.next_retry_at = timezone.now() + timedelta(seconds=wait_seconds)
        event.status = SyncEventStatus.FAILED
    event.save(
        update_fields=[
            "attempts",
            "last_attempt_at",
            "last_error",
            "is_dead_letter",
            "next_retry_at",
            "status",
            "updated_at",
        ]
    )


def reset_failed_events_for_retry(limit: int = 1000) -> int:
    qs = SyncEvent.objects.filter(status=SyncEventStatus.FAILED)[:limit]
    count = 0
    for event in qs:
        event.is_dead_letter = False
        event.next_retry_at = None
        event.last_error = ""
        event.status = SyncEventStatus.PENDING
        event.save(update_fields=["is_dead_letter", "next_retry_at", "last_error", "status", "updated_at"])
        count += 1
    return count


def retry_dead_letters(limit: int = 200) -> int:
    qs = SyncEvent.objects.filter(is_dead_letter=True).order_by("created_at")[:limit]
    count = 0
    for event in qs:
        event.is_dead_letter = False
        event.status = SyncEventStatus.PENDING
        event.next_retry_at = None
        event.last_error = ""
        event.save(
            update_fields=[
                "is_dead_letter",
                "status",
                "next_retry_at",
                "last_error",
                "updated_at",
            ]
        )
        count += 1
    return count


def _eligible_outbound_events(cfg: SyncConfig, limit: int):
    now = timezone.now()
    return SyncEvent.objects.filter(
        status__in=[SyncEventStatus.PENDING, SyncEventStatus.FAILED],
        is_dead_letter=False,
    ).filter(
        Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now)
    ).order_by("created_at")[:limit]


def list_outbox_events(limit: int = 200, since=None, exclude_source_node: str = "") -> list[dict[str, Any]]:
    qs = SyncEvent.objects.filter(is_dead_letter=False).order_by("created_at")
    if since is not None:
        qs = qs.filter(created_at__gt=since)
    if exclude_source_node:
        qs = qs.exclude(source_node=exclude_source_node)
    events = qs[: max(1, min(limit, 1000))]
    return [
        {
            "event_uuid": str(event.event_uuid),
            "source_node": event.source_node,
            "model_label": event.model_label,
            "object_pk": event.object_pk,
            "operation": event.operation,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]


def push_pending_events(limit: int = 200) -> dict[str, Any]:
    cfg = get_or_create_sync_config()
    now = timezone.now()
    summary = {
        "attempted": 0,
        "synced": 0,
        "failed": 0,
        "dead_lettered": 0,
        "skipped": False,
        "detail": "",
    }

    if not _is_online_mode(cfg) or not cfg.push_enabled:
        summary["skipped"] = True
        summary["detail"] = "Sync disabled or offline mode."
        return summary
    if not cfg.remote_base_url:
        summary["skipped"] = True
        summary["detail"] = "Remote base URL not configured."
        return summary

    events = list(_eligible_outbound_events(cfg, limit))
    if not events:
        cfg.last_sync_at = now
        cfg.last_error = ""
        cfg.save(update_fields=["last_sync_at", "last_error", "updated_at"])
        summary["detail"] = "No pending events."
        return summary

    summary["attempted"] = len(events)
    payload = {
        "source_node": cfg.node_id or "",
        "events": [
            {
                "event_uuid": str(event.event_uuid),
                "model_label": event.model_label,
                "object_pk": event.object_pk,
                "operation": event.operation,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }
    endpoint = cfg.remote_base_url.rstrip("/") + "/api/sync/events/ingest/"

    try:
        req = _request_with_auth(cfg, endpoint, method="POST", data=payload)
        with request.urlopen(req, timeout=25) as resp:
            response_data = json.loads(resp.read().decode("utf-8") or "{}")
            accepted = set(response_data.get("accepted_event_uuids") or [])

        for event in events:
            if str(event.event_uuid) in accepted:
                event.status = SyncEventStatus.SYNCED
                event.synced_at = now
                event.last_error = ""
                event.last_attempt_at = now
                event.next_retry_at = None
                event.save(
                    update_fields=[
                        "status",
                        "synced_at",
                        "last_error",
                        "last_attempt_at",
                        "next_retry_at",
                        "updated_at",
                    ]
                )
                summary["synced"] += 1
            else:
                _mark_event_failed(event, "Remote did not accept event.", cfg)
                summary["failed"] += 1
                if event.is_dead_letter:
                    summary["dead_lettered"] += 1

        cfg.last_sync_at = now
        if summary["failed"] == 0:
            cfg.last_success_at = now
            cfg.last_error = ""
        else:
            cfg.last_error = f"{summary['failed']} events failed in last push."
        cfg.save(update_fields=["last_sync_at", "last_success_at", "last_error", "updated_at"])
        summary["detail"] = "Push completed."
        return summary
    except Exception as exc:
        err_msg = str(exc)
        for event in events:
            _mark_event_failed(event, err_msg, cfg)
            summary["failed"] += 1
            if event.is_dead_letter:
                summary["dead_lettered"] += 1
        cfg.last_sync_at = now
        cfg.last_error = err_msg
        cfg.save(update_fields=["last_sync_at", "last_error", "updated_at"])
        summary["detail"] = err_msg
        return summary


def _model_from_label(model_label: str):
    if "." not in model_label:
        return None
    app_label, model_name = model_label.split(".", 1)
    try:
        return apps.get_model(app_label, model_name)
    except Exception:
        return None


def _is_incoming_newer(local_updated_at, incoming_updated_at) -> bool:
    if incoming_updated_at is None:
        return False
    if local_updated_at is None:
        return True
    try:
        return incoming_updated_at >= local_updated_at
    except Exception:
        return False


@transaction.atomic
def apply_inbound_events(limit: int = 200) -> dict[str, Any]:
    cfg = get_or_create_sync_config()
    summary = {"processed": 0, "applied": 0, "skipped": 0, "failed": 0}

    inbound_events = SyncInboundEvent.objects.filter(is_processed=False).order_by("created_at")[:limit]
    for inbound in inbound_events:
        summary["processed"] += 1
        payload = inbound.payload or {}
        source_node = (payload.get("source_node") or inbound.source_node or "").strip()
        if source_node and source_node == (cfg.node_id or "").strip():
            inbound.is_processed = True
            inbound.save(update_fields=["is_processed", "updated_at"])
            summary["skipped"] += 1
            continue

        model_label = payload.get("model_label") or ""
        operation = payload.get("operation") or ""
        object_pk = payload.get("object_pk")
        object_data = payload.get("payload") or {}
        model_cls = _model_from_label(model_label)
        if not model_cls or model_label not in SYNC_MODEL_LABELS:
            inbound.is_processed = True
            inbound.save(update_fields=["is_processed", "updated_at"])
            summary["skipped"] += 1
            continue

        try:
            obj = model_cls.objects.filter(pk=object_pk).first()
            incoming_updated_at = parse_datetime(str(object_data.get("updated_at") or "")) if object_data.get("updated_at") else None
            local_updated_at = getattr(obj, "updated_at", None) if obj else None

            if operation == "delete":
                if obj is not None:
                    if _is_incoming_newer(local_updated_at, incoming_updated_at) or incoming_updated_at is None:
                        obj.delete()
                        summary["applied"] += 1
                    else:
                        summary["skipped"] += 1
                else:
                    summary["skipped"] += 1
            else:
                if obj is not None and cfg.conflict_policy == "last_write_wins":
                    if not _is_incoming_newer(local_updated_at, incoming_updated_at):
                        inbound.is_processed = True
                        inbound.save(update_fields=["is_processed", "updated_at"])
                        summary["skipped"] += 1
                        continue

                write_data = {}
                for field in model_cls._meta.fields:
                    name = field.name
                    if name in {"id", "created_at", "updated_at"}:
                        continue
                    if name in object_data:
                        write_data[name] = object_data[name]
                if obj is None:
                    obj = model_cls(pk=object_pk)
                for key, val in write_data.items():
                    setattr(obj, key, val)
                obj.save()
                summary["applied"] += 1

            inbound.is_processed = True
            inbound.save(update_fields=["is_processed", "updated_at"])
        except Exception:
            summary["failed"] += 1

    return summary


def pull_remote_events(limit: int = 200) -> dict[str, Any]:
    cfg = get_or_create_sync_config()
    summary = {
        "fetched": 0,
        "stored": 0,
        "applied": 0,
        "failed": 0,
        "skipped": False,
        "detail": "",
    }

    if not _is_online_mode(cfg) or not cfg.pull_enabled:
        summary["skipped"] = True
        summary["detail"] = "Pull disabled or offline mode."
        return summary
    if not cfg.remote_base_url:
        summary["skipped"] = True
        summary["detail"] = "Remote base URL not configured."
        return summary

    since = cfg.last_pull_at.isoformat() if cfg.last_pull_at else ""
    query = parse.urlencode(
        {
            "limit": max(1, min(limit, 1000)),
            "since": since,
            "exclude_source_node": cfg.node_id or "",
        }
    )
    endpoint = cfg.remote_base_url.rstrip("/") + f"/api/sync/events/outbox/?{query}"

    try:
        req = _request_with_auth(cfg, endpoint, method="GET")
        with request.urlopen(req, timeout=25) as resp:
            response_data = json.loads(resp.read().decode("utf-8") or "{}")
        events = response_data.get("events") or []
        summary["fetched"] = len(events)

        for event in events:
            event_uuid = event.get("event_uuid")
            source_node = event.get("source_node", "")
            if not event_uuid:
                continue
            _, created = SyncInboundEvent.objects.get_or_create(
                event_uuid=event_uuid,
                source_node=source_node,
                defaults={"payload": event},
            )
            if created:
                summary["stored"] += 1

        apply_summary = apply_inbound_events(limit=max(1, min(limit * 2, 5000)))
        summary["applied"] = apply_summary.get("applied", 0)
        summary["failed"] = apply_summary.get("failed", 0)
        cfg.last_pull_at = timezone.now()
        cfg.last_error = "" if summary["failed"] == 0 else "Inbound apply had failures."
        cfg.save(update_fields=["last_pull_at", "last_error", "updated_at"])
        summary["detail"] = "Pull completed."
        return summary
    except Exception as exc:
        cfg.last_error = str(exc)
        cfg.save(update_fields=["last_error", "updated_at"])
        summary["failed"] = 1
        summary["detail"] = str(exc)
        return summary


def sync_cycle(limit: int = 200) -> dict[str, Any]:
    push_summary = push_pending_events(limit=limit)
    pull_summary = pull_remote_events(limit=limit)
    return {"push": push_summary, "pull": pull_summary}


def start_background_sync_loop(stop_event: threading.Event | None = None, interval_seconds: int | None = None) -> threading.Thread:
    stop = stop_event or threading.Event()

    def _worker():
        while not stop.is_set():
            cfg = get_or_create_sync_config()
            wait_s = interval_seconds or cfg.interval_seconds or 30
            try:
                sync_cycle(limit=200)
            except Exception:
                pass
            stop.wait(max(wait_s, 5))

    t = threading.Thread(target=_worker, name="staylux-sync-loop", daemon=True)
    t.start()
    return t
