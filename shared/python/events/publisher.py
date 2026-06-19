"""
PossKassa — RabbitMQ voqea nashriyotchisi
Asinxron voqealarni yuborish uchun
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from ..utils.config import settings


_connection: aio_pika.RobustConnection | None = None
_channel:    aio_pika.Channel | None = None


async def _get_channel() -> aio_pika.Channel:
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    if _channel is None or _channel.is_closed:
        _channel = await _connection.channel()
    return _channel


async def publish_event(
    routing_key: str,
    payload:     dict[str, Any],
    exchange:    str = "posskassa.events",
) -> None:
    """
    RabbitMQ ga voqea yuboradi.

    Misol:
        await publish_event("sale.created", {"sale_id": "...", "total": 50000})
    """
    channel = await _get_channel()

    exch = await channel.declare_exchange(
        exchange,
        ExchangeType.TOPIC,
        durable=True,
    )

    message_body = {
        "event_id":   str(uuid.uuid4()),
        "event_type": routing_key,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "data":       payload,
    }

    await exch.publish(
        aio_pika.Message(
            body=json.dumps(message_body, default=str).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=routing_key,
    )


# ─── Standart voqea turları ────────────────────────
class Events:
    SALE_CREATED          = "sale.created"
    SALE_REFUNDED         = "sale.refunded"
    SHIFT_OPENED          = "shift.opened"
    SHIFT_CLOSED          = "shift.closed"
    STOCK_UPDATED         = "stock.updated"
    STOCK_LOW             = "stock.low_threshold"
    INTAKE_APPROVED       = "intake.approved"
    FISCAL_SENT           = "fiscal.sent"
    FISCAL_CONFIRMED      = "fiscal.confirmed"
    FISCAL_FAILED         = "fiscal.failed"
    PAYMENT_COMPLETED     = "payment.completed"
