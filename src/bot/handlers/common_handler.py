"""
Common/fallback handlers
"""

from aiogram import F
from aiogram.types import CallbackQuery

from .base_handler import BaseHandler


class CommonHandler(BaseHandler):
    """Router for generic handlers that should work regardless of state."""

    def __init__(self, settings, database):
        super().__init__(settings, database)
        self.register_handlers()

    def register_handlers(self):
        """Register generic handlers with lowest priority semantics.
        Placed in a separate router that is included last to avoid
        shadowing more specific handlers.
        """

        @self.router.callback_query(F.data.startswith("cancel"))
        async def generic_cancel(callback: CallbackQuery):
            """Fallback: delete the message on any 'cancel*' callbacks.
            Useful when users tap old Cancel buttons after state changed.
            """
            try:
                await self.try_delete(callback)
                await callback.answer()
            except Exception:
                # Silently ignore; nothing else to do here
                try:
                    await callback.answer()
                except Exception:
                    pass



