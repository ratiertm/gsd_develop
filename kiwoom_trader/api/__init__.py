"""Kiwoom OpenAPI+ API layer.

Exports all core API components for convenient importing:
    from kiwoom_trader.api import KiwoomAPI, EventHandlerRegistry, ...

Note: KiwoomAPI requires PyQt5 (Windows only). On non-Windows environments,
importing KiwoomAPI directly will fail but other components remain accessible.
"""

from .event_handler import EventHandlerRegistry
from .real_data import RealDataManager
from .session_manager import SessionManager
from .tr_request_queue import TRRequestQueue

try:
    from .kiwoom_api import KiwoomAPI
except ImportError:
    KiwoomAPI = None  # type: ignore[assignment,misc]

__all__ = [
    "KiwoomAPI",
    "EventHandlerRegistry",
    "TRRequestQueue",
    "RealDataManager",
    "SessionManager",
]
