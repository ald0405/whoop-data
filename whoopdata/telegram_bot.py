from __future__ import annotations

import asyncio
import base64
import html
import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram.constants import ParseMode

from whoopdata.agent import settings as agent_settings
from whoopdata.agent.conversation_service import ConversationService, get_conversation_service

load_dotenv()

logger = logging.getLogger(__name__)


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()

    parsed: set[int] = set()
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        parsed.add(int(value))
    return parsed


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_IDS = _parse_int_set(os.getenv("TELEGRAM_ALLOWED_USER_IDS"))
TELEGRAM_ALLOWED_CHAT_IDS = _parse_int_set(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS"))


@dataclass
class OutboundTelegramMessage:
    text: str | None = None
    photo_bytes: bytes | None = None
    voice_bytes: bytes | None = None
    caption: str | None = None
    parse_mode: str | None = None


@dataclass
class ConversationBinding:
    session_id: str | None = None
    thread_id: str | None = None


class TelegramConversationGateway:
    def __init__(
        self,
        *,
        conversation_service: ConversationService | None = None,
        allowed_user_ids: Iterable[int] | None = None,
        allowed_chat_ids: Iterable[int] | None = None,
    ) -> None:
        self._conversation_service = conversation_service or get_conversation_service()
        self._allowed_user_ids = set(allowed_user_ids or ())
        self._allowed_chat_ids = set(allowed_chat_ids or ())
        self._bindings_by_chat: dict[int, ConversationBinding] = {}

    def is_authorized(self, *, user_id: int | None, chat_id: int | None, chat_type: str | None) -> bool:
        if user_id is None or chat_id is None:
            return False

        if chat_type != "private":
            return False

        if self._allowed_user_ids and user_id not in self._allowed_user_ids:
            return False

        if self._allowed_chat_ids and chat_id not in self._allowed_chat_ids:
            return False

        return True

    def build_whoami_messages(
        self, *, user_id: int | None, chat_id: int | None, chat_type: str | None
    ) -> list[OutboundTelegramMessage]:
        return [
            OutboundTelegramMessage(
                text=(
                    "Telegram identity details:\n"
                    f"- user_id: {user_id}\n"
                    f"- chat_id: {chat_id}\n"
                    f"- chat_type: {chat_type}\n\n"
                    "Add these to your `.env` as `TELEGRAM_ALLOWED_USER_IDS` and "
                    "`TELEGRAM_ALLOWED_CHAT_IDS`, then restart the bot to lock it down."
                )
            )
        ]

    async def handle_text_message(
        self,
        *,
        text: str,
        user_id: int | None,
        chat_id: int | None,
        chat_type: str | None,
        image_b64: str | None = None,
    ) -> list[OutboundTelegramMessage]:
        if not self.is_authorized(user_id=user_id, chat_id=chat_id, chat_type=chat_type):
            return []
        binding = self._bindings_by_chat.setdefault(
            chat_id,
            ConversationBinding(
                session_id=f"telegram-chat-{chat_id}",
                thread_id=f"telegram-thread-{chat_id}",
            ),
        )
        binding = self._bindings_by_chat.setdefault(chat_id, ConversationBinding())
        response = await self._conversation_service.send_message(
            message=text,
            session_id=binding.session_id,
            thread_id=binding.thread_id,
            image_b64=image_b64,
            user_id=f"telegram:{user_id}",
            surface="telegram",
        )
        binding.session_id = response.session_id
        binding.thread_id = response.thread_id
        return self._build_response_messages(response.assistant_message, response.artifacts)

    async def handle_voice_message(
        self,
        *,
        voice_bytes: bytes,
        user_id: int | None,
        chat_id: int | None,
        chat_type: str | None,
    ) -> list[OutboundTelegramMessage]:
        """Transcribe a voice note with Whisper, get agent response, and return voice + text."""
        if not self.is_authorized(user_id=user_id, chat_id=chat_id, chat_type=chat_type):
            return []

        # Transcribe
        transcribed_text = await _transcribe_voice(voice_bytes)
        if not transcribed_text:
            return [
                OutboundTelegramMessage(text="Sorry, I couldn't understand that voice message. Try again?")
            ]

        # Get agent response via the normal text path
        text_responses = await self.handle_text_message(
            text=transcribed_text,
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
        )

        # Convert text responses to voice + keep text as fallback
        return await _attach_voice_replies(text_responses)

    async def handle_photo_message(
        self,
        *,
        photo_bytes: bytes,
        caption: str | None,
        user_id: int | None,
        chat_id: int | None,
        chat_type: str | None,
    ) -> list[OutboundTelegramMessage]:
        """Process an incoming photo through the vision-capable agent."""
        if not self.is_authorized(user_id=user_id, chat_id=chat_id, chat_type=chat_type):
            return []

        image_b64 = base64.b64encode(photo_bytes).decode("utf-8")
        text = caption or "What's in this image? Interpret it in the context of my health data."

        return await self.handle_text_message(
            text=text,
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            image_b64=image_b64,
        )

    def _build_response_messages(self, assistant_message: str, artifacts: list) -> list[OutboundTelegramMessage]:
        messages: list[OutboundTelegramMessage] = []

        if assistant_message:
            messages.append(
                OutboundTelegramMessage(
                    text=_format_text_for_telegram_html(assistant_message),
                    parse_mode=ParseMode.HTML,
                )
            )

        for artifact in artifacts:
            if artifact.kind == "python_code" and artifact.content:
                messages.append(
                    OutboundTelegramMessage(
                        text=f"Generated Python Code:\n<pre>{artifact.content}</pre>",
                        parse_mode=ParseMode.HTML,
                    )
                )
            elif artifact.kind == "image" and artifact.content:
                try:
                    photo_bytes = base64.b64decode(artifact.content)
                except Exception:
                    logger.warning("Skipping invalid Telegram image artifact payload")
                    continue
                messages.append(
                    OutboundTelegramMessage(
                        photo_bytes=photo_bytes,
                        caption=artifact.title or "Generated image",
                    )
                )

        return messages


async def _transcribe_voice(voice_bytes: bytes) -> str | None:
    """Transcribe voice bytes using OpenAI Whisper."""
    try:
        client = AsyncOpenAI()
        audio_file = io.BytesIO(voice_bytes)
        audio_file.name = "voice.ogg"
        transcription = await client.audio.transcriptions.create(
            model=agent_settings.WHISPER_MODEL,
            file=audio_file,
        )
        return transcription.text.strip() or None
    except Exception:
        logger.exception("Voice transcription failed")
        return None


async def _text_to_speech(text: str) -> bytes | None:
    """Convert text to speech using OpenAI TTS. Returns opus bytes or None."""
    try:
        client = AsyncOpenAI()
        response = await client.audio.speech.create(
            model=agent_settings.TTS_MODEL,
            voice=agent_settings.TTS_VOICE,
            input=text,
            instructions=agent_settings.TTS_INSTRUCTIONS,
            response_format="opus",
        )
        return response.content
    except Exception:
        logger.exception("Text-to-speech generation failed")
        return None


async def _attach_voice_replies(
    text_responses: list[OutboundTelegramMessage],
) -> list[OutboundTelegramMessage]:
    """For each text response, generate a voice version and include both."""
    result: list[OutboundTelegramMessage] = []
    for msg in text_responses:
        # Only convert pure text messages to voice (not photos/code)
        if msg.text and msg.photo_bytes is None:
            plain_text = _strip_html_tags(msg.text)
            voice_data = await _text_to_speech(plain_text)
            if voice_data:
                result.append(OutboundTelegramMessage(voice_bytes=voice_data))
        # Always include the original message as fallback
        result.append(msg)
    return result


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags for TTS input."""
    return re.sub(r"<[^>]+>", "", text)


def _format_text_for_telegram_html(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^\n*][^*]*?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^\n*][^*]*?)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"^### (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^## (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^# (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    return escaped


def _build_gateway() -> TelegramConversationGateway:
    return TelegramConversationGateway(
        allowed_user_ids=TELEGRAM_ALLOWED_USER_IDS,
        allowed_chat_ids=TELEGRAM_ALLOWED_CHAT_IDS,
    )


async def _reply(update, messages: list[OutboundTelegramMessage]) -> None:
    message = update.effective_message
    if message is None:
        return

    for outbound in messages:
        if outbound.voice_bytes is not None:
            await message.reply_voice(voice=outbound.voice_bytes)
        elif outbound.photo_bytes is not None:
            await message.reply_photo(photo=outbound.photo_bytes, caption=outbound.caption)
        elif outbound.text:
            await message.reply_text(outbound.text, parse_mode=outbound.parse_mode)


async def start_command(update, context) -> None:
    gateway: TelegramConversationGateway = context.application.bot_data["gateway"]
    user = update.effective_user
    chat = update.effective_chat

    intro = [
        OutboundTelegramMessage(
            text=(
                "Health Data Agent is online.\n"
                "Use `/whoami` to capture your Telegram IDs for allowlisting, then add "
                "`TELEGRAM_ALLOWED_USER_IDS` and `TELEGRAM_ALLOWED_CHAT_IDS` to `.env`."
            )
        )
    ]
    if not gateway._allowed_user_ids and not gateway._allowed_chat_ids:
        intro.extend(
            gateway.build_whoami_messages(
                user_id=getattr(user, "id", None),
                chat_id=getattr(chat, "id", None),
                chat_type=getattr(chat, "type", None),
            )
        )
    await _reply(update, intro)


async def whoami_command(update, context) -> None:
    gateway: TelegramConversationGateway = context.application.bot_data["gateway"]
    user = update.effective_user
    chat = update.effective_chat
    await _reply(
        update,
        gateway.build_whoami_messages(
            user_id=getattr(user, "id", None),
            chat_id=getattr(chat, "id", None),
            chat_type=getattr(chat, "type", None),
        ),
    )


async def text_message(update, context) -> None:
    gateway: TelegramConversationGateway = context.application.bot_data["gateway"]
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    text = getattr(message, "text", None)
    if not text:
        return

    responses = await gateway.handle_text_message(
        text=text,
        user_id=getattr(user, "id", None),
        chat_id=getattr(chat, "id", None),
        chat_type=getattr(chat, "type", None),
    )
    await _reply(update, responses)


async def voice_message(update, context) -> None:
    gateway: TelegramConversationGateway = context.application.bot_data["gateway"]
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    voice = getattr(message, "voice", None) or getattr(message, "audio", None)
    if voice is None:
        return

    # Send a brief indicator so the user knows we're processing
    await message.reply_text("🎙️ Transcribing…")

    try:
        tg_file = await voice.get_file()
        voice_data = await tg_file.download_as_bytearray()
    except Exception:
        logger.exception("Failed to download voice file from Telegram")
        await message.reply_text("Sorry, I couldn't download that voice message.")
        return

    responses = await gateway.handle_voice_message(
        voice_bytes=bytes(voice_data),
        user_id=getattr(user, "id", None),
        chat_id=getattr(chat, "id", None),
        chat_type=getattr(chat, "type", None),
    )
    await _reply(update, responses)


async def photo_message(update, context) -> None:
    gateway: TelegramConversationGateway = context.application.bot_data["gateway"]
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    photos = getattr(message, "photo", None)
    if not photos:
        return

    # Use the highest-resolution version (last in the list)
    try:
        tg_file = await photos[-1].get_file()
        photo_data = await tg_file.download_as_bytearray()
    except Exception:
        logger.exception("Failed to download photo from Telegram")
        await message.reply_text("Sorry, I couldn't download that photo.")
        return

    caption = getattr(message, "caption", None)
    responses = await gateway.handle_photo_message(
        photo_bytes=bytes(photo_data),
        caption=caption,
        user_id=getattr(user, "id", None),
        chat_id=getattr(chat, "id", None),
        chat_type=getattr(chat, "type", None),
    )
    await _reply(update, responses)


async def error_handler(update, context) -> None:
    logger.exception("Telegram bot error: %s", context.error)
    if getattr(update, "effective_message", None) is not None:
        await update.effective_message.reply_text("Sorry, I hit an error processing that message.")


def build_application(gateway: TelegramConversationGateway | None = None):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start the Telegram bot")

    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.bot_data["gateway"] = gateway or _build_gateway()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("whoami", whoami_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, photo_message))
    application.add_error_handler(error_handler)
    return application


async def run_bot() -> None:
    application = build_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram bot polling started")
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())
