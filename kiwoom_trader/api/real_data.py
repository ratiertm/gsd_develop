"""Real-time data subscription and dispatch manager.

Manages SetRealReg subscriptions with auto screen number generation,
extracts FID values within OnReceiveRealData context, and dispatches
parsed data dicts to registered subscribers (observer pattern).
"""

from loguru import logger

from kiwoom_trader.config.constants import FID, SCREEN


# Standard FIDs to extract on every real-time event
_STANDARD_FIDS = [
    FID.CURRENT_PRICE,
    FID.VOLUME,
    FID.EXEC_VOLUME,
    FID.OPEN_PRICE,
    FID.HIGH_PRICE,
    FID.LOW_PRICE,
]


class RealDataManager:
    """Real-time data subscription and dispatch manager.

    Handles SetRealReg lifecycle, auto-generates screen numbers,
    and dispatches parsed FID data to subscribers.
    """

    def __init__(self, kiwoom_api, session_manager=None):
        """Initialize RealDataManager.

        Args:
            kiwoom_api: KiwoomAPI instance for COM calls.
            session_manager: Optional SessionManager for subscription tracking
                (enables restore after reconnect).
        """
        self._api = kiwoom_api
        self._session_manager = session_manager
        self._subscribers: dict[str, list] = {}  # real_type -> [callbacks]
        self._subscriptions: list[dict] = []  # for tracking/restore
        self._screen_counter = SCREEN.REAL_BASE

    def subscribe(
        self,
        code_list: str,
        fid_list: str,
        screen_no: str | None = None,
        real_type: str = "1",
    ):
        """Subscribe to real-time data via SetRealReg.

        Args:
            code_list: Semicolon-separated stock codes (e.g., "005930;000660")
            fid_list: Semicolon-separated FID numbers (e.g., "10;13;15")
            screen_no: 4-digit screen number. Auto-generated if None.
            real_type: "0" = replace existing, "1" = add to existing
        """
        if screen_no is None:
            screen_no = self._next_screen_no()

        self._api.set_real_reg(screen_no, code_list, fid_list, real_type)

        self._subscriptions.append(
            {
                "screen_no": screen_no,
                "code_list": code_list,
                "fid_list": fid_list,
                "real_type": real_type,
            }
        )
        logger.info(
            f"Real subscription: screen={screen_no}, codes={code_list}, "
            f"fids={fid_list}"
        )

        if self._session_manager:
            self._session_manager.track_real_subscription(
                screen_no, code_list, fid_list, real_type
            )

    def unsubscribe(self, screen_no: str, code: str):
        """Remove real-time data registration.

        Args:
            screen_no: Screen number of the subscription.
            code: Stock code to unsubscribe.
        """
        self._api.set_real_remove(screen_no, code)
        logger.info(f"Real unsubscribe: screen={screen_no}, code={code}")

    def register_subscriber(self, real_type: str, callback):
        """Register a callback for a real-time data type.

        Multiple callbacks can be registered for the same real_type.

        Args:
            real_type: Real-time data type string (e.g., "주식체결")
            callback: Callable(code, data_dict) to receive parsed data.
        """
        self._subscribers.setdefault(real_type, []).append(callback)
        logger.debug(f"Real subscriber registered: {real_type}")

    def on_real_data(self, code: str, real_type: str, real_data: str):
        """Handle OnReceiveRealData event.

        Extracts standard FID values via get_comm_real_data (must be called
        within the event context), builds a dict, and dispatches to all
        subscribers registered for the real_type.

        Args:
            code: Stock code that received data.
            real_type: Real-time data type string.
            real_data: Raw real data string (not used directly -- FIDs
                are extracted via get_comm_real_data).
        """
        # Extract standard FIDs within event context
        data_dict = {}
        for fid in _STANDARD_FIDS:
            data_dict[fid] = self._api.get_comm_real_data(code, fid)

        # Dispatch to subscribers
        handlers = self._subscribers.get(real_type, [])
        for handler in handlers:
            handler(code, data_dict)

    def _next_screen_no(self) -> str:
        """Generate the next auto-incremented screen number.

        Returns:
            4-digit string starting from SCREEN.REAL_BASE (5000).
        """
        screen_no = f"{self._screen_counter:04d}"
        self._screen_counter += 1
        return screen_no
