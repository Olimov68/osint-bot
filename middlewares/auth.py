from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from config import ALLOWED_USER_ID

class AuthMiddleware(BaseMiddleware):
    """
    Faqat ALLOWED_USER_ID ga ega adminga xizmat ko'rsatish filtri.
    Begona foydalanuvchilarning har qanday so'rovlari e'tiborsiz qoldiriladi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user or user.id != ALLOWED_USER_ID:
            # Begona shaxs — butunlay e'tiborsiz qoldiramiz (hech qanday javob qaytmaydi)
            return

        return await handler(event, data)
