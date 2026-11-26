# tests

```console
uv run pytest
```

| File | What it checks |
|---|---|
| [`test_bot.py`](test_bot.py) | The assistant, as text through the LLM Gateway: it uses `get_current_time` for the right place, doesn't make up a time for somewhere without a time zone, keeps replies short and speakable, and hangs up after goodbye |
| [`test_tts.py`](test_tts.py) | `AssemblyAITTSService` against the live API: a reply with word timings, and an interruption |
| [`test_tts_offline.py`](test_tts_offline.py) | A mocked TTS WebSocket omits word timings for the first reply. Both replies finish and the second still has word timings. |

`test_bot.py` runs the same instructions, tool schemas and tool functions as `src/bot.py`, without audio or a Pipecat pipeline. Tool calls are checked exactly; wording is judged by another LLM. The live tests in `test_bot.py` and `test_tts.py` need `ASSEMBLYAI_API_KEY` and are skipped without it. The offline test needs no key.

Run the LLM tests more than once when changing the instructions, a tool or the model. Run the TTS tests when changing the TTS configuration. For each new tool or behavior, add a test like these; the [add-a-tool skill](../skills/add-a-tool/SKILL.md) has an example.
