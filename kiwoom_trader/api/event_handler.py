"""Event routing registry for TR responses and real-time market data.

Routes OnReceiveTrData by rq_name and OnReceiveRealData by real_type
to registered callback functions. Standalone module with no COM dependencies.
"""

from typing import Callable, Dict

from loguru import logger


class EventHandlerRegistry:
    """Routes TR responses and real-time data to registered handlers.

    TR handlers: one callback per rq_name (last registration wins).
    Real handlers: multiple callbacks per real_type (observer pattern).
    """

    def __init__(self):
        self._tr_handlers: Dict[str, Callable] = {}
        self._real_handlers: Dict[str, list[Callable]] = {}

    def register_tr_handler(self, rq_name: str, handler: Callable):
        """Register a callback for a specific TR request name.

        Replaces any previously registered handler for the same rq_name.
        """
        self._tr_handlers[rq_name] = handler
        logger.debug(f"TR handler registered: {rq_name}")

    def register_real_handler(self, real_type: str, handler: Callable):
        """Register a callback for a real-time data type.

        Multiple handlers can be registered for the same real_type (observer pattern).
        """
        self._real_handlers.setdefault(real_type, []).append(handler)
        logger.debug(f"Real handler registered: {real_type}")

    def handle_tr_data(self, rq_name: str, *args):
        """Dispatch TR response data to the registered handler.

        Logs a warning if no handler is registered for the given rq_name.
        """
        handler = self._tr_handlers.get(rq_name)
        if handler:
            handler(*args)
        else:
            logger.warning(f"No TR handler for: {rq_name}")

    def handle_real_data(self, real_type: str, code: str, data: str):
        """Dispatch real-time data to all registered handlers for the type.

        Silently does nothing if no handlers are registered.
        """
        handlers = self._real_handlers.get(real_type, [])
        for handler in handlers:
            handler(code, data)
