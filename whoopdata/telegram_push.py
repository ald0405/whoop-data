"""Proactive Telegram push — sends agent-generated messages to Telegram.

The message goes through ConversationService so it lands in the same
checkpointed thread the Telegram bot uses.  When the user replies in
Telegram, the bot handler picks up the same thread from Postgres and
the conversation continues seamlessly.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from whoopdata.agent.conversation_service import (
    ConversationService,
    get_conversation_service,
)
from whoopdata.telegram_bot import (
    format_text_for_telegram_html,
    format_text_for_telegram_plain,
    session_id_for_chat,
    thread_id_for_chat,
)

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_PROACTIVE_FORMAT = os.getenv("TELEGRAM_PROACTIVE_FORMAT", "plain").strip().lower()


@dataclass
class PushResult:
    """PushResult type definition."""
    assistant_message: str
    telegram_message_id: int | None = None


async def push_to_telegram(
    *,
    chat_id: int,
    prompt: str,
    conversation_service: ConversationService | None = None,
    bot_token: str | None = None,
    telegram_format: str | None = None,
) -> PushResult:
    """Send a proactive agent message to a Telegram chat.

    1. Routes ``prompt`` through the shared ConversationService so the
       exchange is checkpointed in the same thread the Telegram bot uses.
    2. Delivers the agent's response to the Telegram chat via Bot API.

    Args:
        chat_id: Telegram chat to push to.
        prompt: Internal prompt that triggers the agent (the user won't
                see this — only the agent's response is sent).
        conversation_service: Optional; defaults to the singleton.
        bot_token: Optional; defaults to TELEGRAM_BOT_TOKEN env var.

    Returns:
        PushResult with the assistant message and Telegram message ID.
    """
    svc = conversation_service or get_conversation_service()
    token = bot_token or TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for proactive push")

    # Send through the conversation service on the same thread the bot uses
    response = await svc.send_message(
        message=prompt,
        session_id=session_id_for_chat(chat_id),
        thread_id=thread_id_for_chat(chat_id),
        user_id=f"telegram:{chat_id}",
        surface="telegram",
    )

    # Deliver the agent's response to Telegram.
    from telegram import Bot
    from telegram.constants import ParseMode

    bot = Bot(token=token)

    raw_fmt = telegram_format or "plain"
    fmt = raw_fmt.strip().lower()
    if fmt == "html":
        formatted = format_text_for_telegram_html(response.assistant_message)
        msg = await bot.send_message(
            chat_id=chat_id,
            text=formatted,
            parse_mode=ParseMode.HTML,
        )
    else:
        formatted = format_text_for_telegram_plain(response.assistant_message)
        msg = await bot.send_message(
            chat_id=chat_id,
            text=formatted,
        )
    telegram_message_id = msg.message_id

    logger.info(
        "Proactive push sent to chat_id=%s, message_id=%s",
        chat_id,
        telegram_message_id,
    )

    return PushResult(
        assistant_message=formatted,
        telegram_message_id=telegram_message_id,
    )
