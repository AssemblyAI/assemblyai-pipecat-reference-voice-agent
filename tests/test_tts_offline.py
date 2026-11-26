"""Exercise the starter's TTS service in a pipeline with an in-memory provider."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock

from pipecat.frames.frames import (
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TTSAudioRawFrame,
    TTSStoppedFrame,
    TTSTextFrame,
)
from pipecat.tests.utils import SleepFrame, run_test
from websockets.protocol import State

from bot import AssemblyAITTSService

SAMPLE_RATE = 24000
AUDIO_DURATION_MS = 100
AUDIO = base64.b64encode(bytes(SAMPLE_RATE * 2 * AUDIO_DURATION_MS // 1000)).decode()


class TTSConnection:
    def __init__(self):
        self.state = State.OPEN
        self.messages = asyncio.Queue()
        self.flush_id = 0
        self.enqueue(type="Begin", id="test-session", configuration={"word_boundaries": True})

    def enqueue(self, **frame):
        self.messages.put_nowait(json.dumps(frame))

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.messages.get()

    async def send(self, raw):
        if json.loads(raw)["type"] != "Flush":
            return
        flush_id = self.flush_id
        self.flush_id += 1
        self.enqueue(type="Audio", flush_id=flush_id, audio=AUDIO)
        self.enqueue(type="FlushDone", flush_id=flush_id, audio_duration_ms=AUDIO_DURATION_MS)
        # The first flush omits timings even though Begin advertised them.
        if flush_id == 1:
            self.enqueue(
                type="WordBoundaries",
                flush_id=flush_id,
                audio_start_ms=AUDIO_DURATION_MS,
                words=[
                    {"word": "Second", "start": 110, "end": 140, "confidence": 1.0},
                    {"word": "reply.", "start": 150, "end": 190, "confidence": 1.0},
                ],
            )

    async def close(self):
        self.state = State.CLOSED


def reply(text):
    return [LLMFullResponseStartFrame(), LLMTextFrame(text), LLMFullResponseEndFrame()]


async def test_next_reply_plays_when_word_boundaries_are_missing(monkeypatch):
    connection = TTSConnection()
    connect = AsyncMock(return_value=connection)
    tts = AssemblyAITTSService(api_key="offline-fixture", sample_rate=SAMPLE_RATE)
    monkeypatch.setattr(tts, "_websocket_connect", connect)

    frames, errors = await asyncio.wait_for(
        run_test(
            tts,
            frames_to_send=[*reply("First."), SleepFrame(sleep=1.25), *reply("Second reply.")],
        ),
        timeout=8,
    )

    assert not errors
    connect.assert_awaited_once()
    audio = [frame for frame in frames if isinstance(frame, TTSAudioRawFrame)]
    stops = [frame for frame in frames if isinstance(frame, TTSStoppedFrame)]
    assert len(audio) == 2
    assert audio[0].context_id != audio[1].context_id
    assert [frame.context_id for frame in stops] == [frame.context_id for frame in audio]
    assert frames.index(audio[0]) < frames.index(stops[0]) < frames.index(audio[1])
    second_words = [
        frame.text
        for frame in frames
        if isinstance(frame, TTSTextFrame) and frame.context_id == audio[1].context_id
    ]
    assert second_words == ["Second", "reply."]
