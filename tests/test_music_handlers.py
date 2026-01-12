from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.db.enum import UserRole
from bot.handlers.music import back, entry, lyrics, style, title
from bot.keyboards.enums import MusicBackTarget
from bot.states import BaseUserState, MusicGenerationState
from bot.utils.music_state import update_music_data
from bot.utils.texts import MUSIC_PROMPT_AI_TEXT
from tests.fakes import DummyCallbackQuery, DummyMessage, DummyState

pytestmark = pytest.mark.asyncio


async def test_music_entry_resets_state(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    monkeypatch,
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(entry, "edit_or_answer", edit_or_answer)

    await entry.music_entry(dummy_query, dummy_state)

    assert dummy_state.state is None
    edit_or_answer.assert_awaited_once()


async def test_music_back_home(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    user_factory,
    monkeypatch,
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(back, "edit_or_answer", edit_or_answer)
    user = user_factory(role=UserRole.ADMIN.value)

    callback_data = SimpleNamespace(target=MusicBackTarget.HOME.value)
    await back.music_back(dummy_query, callback_data, dummy_state, user)

    assert dummy_state.state == BaseUserState.main
    edit_or_answer.assert_awaited_once()


async def test_music_back_prompt_uses_source(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_user,
    monkeypatch,
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(back, "edit_or_answer", edit_or_answer)
    await update_music_data(dummy_state, prompt_source="ai")

    callback_data = SimpleNamespace(target=MusicBackTarget.PROMPT.value)
    await back.music_back(dummy_query, callback_data, dummy_state, dummy_user)

    assert dummy_state.state == MusicGenerationState.prompt
    assert edit_or_answer.call_args.kwargs["text"] == MUSIC_PROMPT_AI_TEXT


async def test_lyrics_ai_sets_prompt_state(
    dummy_query: DummyCallbackQuery, dummy_state: DummyState, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(lyrics, "edit_or_answer", edit_or_answer)

    await lyrics.lyrics_ai(dummy_query, dummy_state)

    assert dummy_state.state == MusicGenerationState.prompt
    edit_or_answer.assert_awaited_once()


async def test_lyrics_manual_sets_prompt_state(
    dummy_query: DummyCallbackQuery, dummy_state: DummyState, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(lyrics, "edit_or_answer", edit_or_answer)

    await lyrics.lyrics_manual(dummy_query, dummy_state)

    assert dummy_state.state == MusicGenerationState.prompt
    edit_or_answer.assert_awaited_once()


async def test_lyrics_instrumental_sets_prompt_state(
    dummy_query: DummyCallbackQuery, dummy_state: DummyState, monkeypatch
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(lyrics, "edit_or_answer", edit_or_answer)

    await lyrics.lyrics_instrumental(dummy_query, dummy_state)

    assert dummy_state.state == MusicGenerationState.prompt
    edit_or_answer.assert_awaited_once()


async def test_prompt_received_ai_flow(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    dummy_message.text = "prompt"
    await update_music_data(dummy_state, prompt_source="ai")

    charge_user_credits = AsyncMock(return_value=True)
    monkeypatch.setattr(lyrics, "charge_user_credits", charge_user_credits)

    client = SimpleNamespace(generate_song_text=AsyncMock(return_value="lyrics"))
    monkeypatch.setattr(lyrics, "_lyrics_client", lambda: client)

    record_usage_event = AsyncMock()
    monkeypatch.setattr(lyrics, "record_usage_event", record_usage_event)

    await lyrics.prompt_received(
        dummy_message,
        dummy_state,
        dummy_user,
        dummy_session,
        SimpleNamespace(),
        dummy_redis,
    )

    assert dummy_state.state == MusicGenerationState.title
    charge_user_credits.assert_awaited_once()


async def test_title_received_moves_to_style(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
) -> None:
    dummy_message.text = "Title"

    await title.title_received(dummy_message, dummy_state)

    assert dummy_state.state == MusicGenerationState.style


async def test_style_received_starts_generation(
    dummy_message: DummyMessage,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    dummy_message.text = "Style"
    start_generation = AsyncMock()
    monkeypatch.setattr(style, "start_generation", start_generation)

    await style.style_received(
        dummy_message,
        dummy_state,
        dummy_user,
        dummy_session,
        SimpleNamespace(),
        dummy_redis,
    )

    start_generation.assert_awaited_once()


async def test_style_selected_custom(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    edit_or_answer = AsyncMock()
    monkeypatch.setattr(style, "edit_or_answer", edit_or_answer)

    callback_data = SimpleNamespace(style="custom")
    await style.style_selected(
        dummy_query,
        callback_data,
        dummy_state,
        dummy_user,
        dummy_session,
        SimpleNamespace(),
        dummy_redis,
    )

    edit_or_answer.assert_awaited_once()


async def test_style_selected_preset_starts_generation(
    dummy_query: DummyCallbackQuery,
    dummy_state: DummyState,
    dummy_user,
    dummy_session,
    dummy_redis,
    monkeypatch,
) -> None:
    start_generation = AsyncMock()
    monkeypatch.setattr(style, "start_generation", start_generation)

    callback_data = SimpleNamespace(style="Rock")
    await style.style_selected(
        dummy_query,
        callback_data,
        dummy_state,
        dummy_user,
        dummy_session,
        SimpleNamespace(),
        dummy_redis,
    )

    start_generation.assert_awaited_once()
