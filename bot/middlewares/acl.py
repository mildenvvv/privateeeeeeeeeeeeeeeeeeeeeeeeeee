from aiogram.types import Update, Message, CallbackQuery
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Dict, Any, Union

from utils.logger import log 

class AccessControlMiddleware(BaseMiddleware):
    def __init__(self, allowed_users: set[int]):
        self.allowed_users = allowed_users
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Any],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if event.message:
            user_id = event.message.from_user.id
            event_type = "message"
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            event_type = "callback_query"
        elif event.inline_query:
            user_id = event.inline_query.from_user.id
            event_type = "inline_query"

        if user_id is None:
            log.warning(f"Не удалось получить user_id для обновления: {event}")
            return await handler(event, data)

        if not self.allowed_users: 
            log.warning(f"Список разрешенных пользователей пуст. Отклонен user {user_id} ({event_type})")
            if event.message:
                await event.message.answer("Бот временно недоступен. Пожалуйста, попробуйте позже.")
            elif event.callback_query:
                await event.callback_query.answer("Бот временно недоступен.", show_alert=True)
            return
            
        if user_id not in self.allowed_users:
            log.info(f"Доступ запрещен для пользователя {user_id} ({event_type})")
            if event.message:
                await event.message.answer("Извините, у вас нет доступа к этому боту. Обратитесь к @mildeks для получения доступа.")
            elif event.callback_query:
                await event.callback_query.answer("Извините, у вас нет доступа к этому боту. Обратитесь к @mildeks для получения доступа.", show_alert=True)
            return
        
        log.debug(f"Доступ разрешен для пользователя {user_id} ({event_type})")
        return await handler(event, data)