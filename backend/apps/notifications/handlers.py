"""Outbox handlers: one per catalogued notification event type (TR-11)."""

from common.events.services import register_handler

from .catalogue import CATALOGUE
from .services import HANDLER_LEVELS, handle_event


def _register(event_type: str) -> None:
    @register_handler(event_type, lock_levels=HANDLER_LEVELS)
    def handler(event, payload):
        handle_event(event, payload)


for _event_type in CATALOGUE:
    _register(_event_type)
