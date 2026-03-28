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
_MARKDOWN_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")


def _parse_int_set(raw: str | None) -> set[int]:
    """ parse int set.

    Args:
        raw: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    
    """
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
    """OutboundTelegramMessage data structure or service type.

    
    """
    text: str | None = None
    photo_bytes: bytes | None = None
    voice_bytes: bytes | None = None
    caption: str | None = None
    parse_mode: str | None = None


def thread_id_for_chat(chat_id: int) -> str:
    """Canonical thread ID for a Telegram chat. Used by both the bot and proactive push."""
    return f"telegram-thread-{chat_id}"


def session_id_for_chat(chat_id: int) -> str:
    """Canonical session ID for a Telegram chat. Used by both the bot and proactive push."""
    return f"telegram-chat-{chat_id}"


@dataclass
class ConversationBinding:
    """ConversationBinding data structure or service type.

    
    """
    session_id: str | None = None
    thread_id: str | None = None


class TelegramConversationGateway:
    """TelegramConversationGateway data structure or service type.

    
    """
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

    def is_authorized(
        self, *, user_id: int | None, chat_id: int | None, chat_type: str | None
    ) -> bool:
        """Is authorized.

        Args:
            user_id: Input parameter used by this routine.
            chat_id: Input parameter used by this routine.
            chat_type: Input parameter used by this routine.

        Returns:
            Computed result for this routine.

        Example:
            # Example usage
            result = is_authorized(user_id=..., chat_id=..., chat_type=...)
            _ = result

        
        """
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
        """Build whoami messages.

        Args:
            user_id: Input parameter used by this routine.
            chat_id: Input parameter used by this routine.
            chat_type: Input parameter used by this routine.

        Returns:
            Computed result for this routine.

        Example:
            # Example usage
            result = build_whoami_messages(user_id=..., chat_id=..., chat_type=...)
            _ = result

        
        """
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
        """Handle text message.

        Args:
            text: Input parameter used by this routine.
            user_id: Input parameter used by this routine.
            chat_id: Input parameter used by this routine.
            chat_type: Input parameter used by this routine.
            image_b64: Input parameter used by this routine.

        Returns:
            Computed result for this routine.

        Example:
            # Example usage
            result = await handle_text_message(text=..., user_id=..., chat_id=..., chat_type=..., image_b64=...)
            _ = result

        
        """
        if not self.is_authorized(user_id=user_id, chat_id=chat_id, chat_type=chat_type):
            return []
        binding = self._bindings_by_chat.setdefault(
            chat_id,
            ConversationBinding(
                session_id=session_id_for_chat(chat_id),
                thread_id=thread_id_for_chat(chat_id),
            ),
        )
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
                OutboundTelegramMessage(
                    text="Sorry, I couldn't understand that voice message. Try again?"
                )
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

    def _build_response_messages(
        self, assistant_message: str, artifacts: list
    ) -> list[OutboundTelegramMessage]:
        """ build response messages.

        Args:
            assistant_message: Input parameter used by this routine.
            artifacts: Input parameter used by this routine.

        Returns:
            Computed result for this routine.

        
        """
        messages: list[OutboundTelegramMessage] = []

        if assistant_message:
            messages.append(
                OutboundTelegramMessage(
                    text=format_text_for_telegram_html(assistant_message),
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


def _strip_markdown_inline_markup(text: str) -> str:
    """ strip markdown inline markup.

    Args:
        text: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    
    """
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"\*\*([^\n*][^*]*?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^\n*][^*]*?)\*(?!\*)", r"\1", text)
    text = re.sub(r"__([^\n_][^_]*?)__", r"\1", text)
    text = re.sub(r"(?<!_)_([^\n_][^_]*?)_(?!_)", r"\1", text)
    return text


def _normalize_telegram_plain_line(text: str) -> str:
    """ normalize telegram plain line.

    Args:
        text: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    
    """
    line = text.strip()
    if not line:
        return ""

    line = re.sub(r"^#{1,6}\s+", "", line)
    line = re.sub(r"^\s*[-*]\s+", "• ", line)
    line = re.sub(r"^\s*\d+[.)]\s+", "• ", line)
    line = _strip_markdown_inline_markup(line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _flatten_markdown_table_row(line: str) -> str:
    """ flatten markdown table row.

    Args:
        line: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    
    """
    cells = [_normalize_telegram_plain_line(cell) for cell in line.strip().strip("|").split("|")]
    cells = [cell for cell in cells if cell]
    if not cells:
        return ""
    if len(cells) == 2:
        return f"{cells[0]}: {cells[1]}"
    return " • ".join(cells)


def _truncate_telegram_plain_text(text: str, *, max_chars: int) -> str:
    """ truncate telegram plain text.

    Args:
        text: Input parameter used by this routine.
        max_chars: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars].rstrip()
    preferred_cutoff = max_chars // 2
    cut_positions = (
        truncated.rfind("\n"),
        truncated.rfind(". "),
        truncated.rfind("? "),
        truncated.rfind("! "),
        truncated.rfind(" "),
    )
    cut_at = max((pos for pos in cut_positions if pos >= preferred_cutoff), default=-1)
    if cut_at >= 0:
        pair = truncated[cut_at : cut_at + 2]
        if pair in {". ", "? ", "! "}:
            truncated = truncated[: cut_at + 1]
        else:
            truncated = truncated[:cut_at]

    return truncated.rstrip(" ,;:-") + "…"


def format_text_for_telegram_plain(
    text: str,
    *,
    max_chars: int = 450,
    max_lines: int = 4,
) -> str:
    """Format text for telegram plain.

    Args:
        text: Input parameter used by this routine.
        max_chars: Input parameter used by this routine.
        max_lines: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    Example:
        # Example usage
        result = format_text_for_telegram_plain(text=..., max_chars=..., max_lines=...)
        _ = result

    
    """
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines: list[str] = []
    in_code_block = False
    index = 0

    while index < len(raw_lines):
        raw_line = raw_lines[index]
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            index += 1
            continue

        if in_code_block:
            line = _normalize_telegram_plain_line(raw_line)
            if line:
                cleaned_lines.append(line)
            index += 1
            continue

        if (
            stripped.count("|") >= 2
            and index + 1 < len(raw_lines)
            and _MARKDOWN_TABLE_SEPARATOR_RE.match(raw_lines[index + 1].strip())
        ):
            index += 2
            while index < len(raw_lines):
                table_line = raw_lines[index].strip()
                if not table_line or table_line.count("|") < 2:
                    break
                flattened = _flatten_markdown_table_row(table_line)
                if flattened:
                    cleaned_lines.append(flattened)
                index += 1
            continue

        if _MARKDOWN_TABLE_SEPARATOR_RE.match(stripped):
            index += 1
            continue

        if stripped.count("|") >= 2:
            flattened = _flatten_markdown_table_row(stripped)
            if flattened:
                cleaned_lines.append(flattened)
            index += 1
            continue

        line = _normalize_telegram_plain_line(raw_line)
        if line:
            cleaned_lines.append(line)
        index += 1

    if not cleaned_lines:
        fallback = _normalize_telegram_plain_line(text) or text.strip()
        return _truncate_telegram_plain_text(fallback, max_chars=max_chars)

    compact_lines = cleaned_lines[:max_lines]
    compact = "\n".join(compact_lines)
    if len(cleaned_lines) > max_lines:
        compact = compact.rstrip(" ,;:-") + "…"
    return _truncate_telegram_plain_text(compact, max_chars=max_chars)


def format_text_for_telegram_html(text: str) -> str:
    """Format text for telegram html.

    Args:
        text: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    Example:
        # Example usage
        result = format_text_for_telegram_html(text=...)
        _ = result

    
    """
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^\n*][^*]*?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^\n*][^*]*?)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"^### (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^## (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^# (.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    return escaped


def _build_gateway() -> TelegramConversationGateway:
    """ build gateway.

    Returns:
        Computed result for this routine.

    
    """
    return TelegramConversationGateway(
        allowed_user_ids=TELEGRAM_ALLOWED_USER_IDS,
        allowed_chat_ids=TELEGRAM_ALLOWED_CHAT_IDS,
    )


async def _reply(update, messages: list[OutboundTelegramMessage]) -> None:
    """ reply.

    Args:
        update: Input parameter used by this routine.
        messages: Input parameter used by this routine.

    
    """
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
    """Start command.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await start_command(update=..., context=...)
        _ = result

    
    """
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
    """Whoami command.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await whoami_command(update=..., context=...)
        _ = result

    
    """
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
    """Text message.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await text_message(update=..., context=...)
        _ = result

    
    """
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
    """Voice message.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await voice_message(update=..., context=...)
        _ = result

    
    """
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
    """Photo message.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await photo_message(update=..., context=...)
        _ = result

    
    """
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
    """Error handler.

    Args:
        update: Input parameter used by this routine.
        context: Input parameter used by this routine.

    Example:
        # Example usage
        result = await error_handler(update=..., context=...)
        _ = result

    
    """
    logger.exception("Telegram bot error: %s", context.error)
    if getattr(update, "effective_message", None) is not None:
        await update.effective_message.reply_text("Sorry, I hit an error processing that message.")


def build_application(gateway: TelegramConversationGateway | None = None):
    """Build application.

    Args:
        gateway: Input parameter used by this routine.

    Returns:
        Computed result for this routine.

    Example:
        # Example usage
        result = build_application(gateway=...)
        _ = result

    
    """
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
    """Run bot.

    Example:
        # Example usage
        result = await run_bot()
        _ = result

    
    """
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
    """Main.

    Example:
        # Example usage
        result = main()
        _ = result

    
    """
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())
