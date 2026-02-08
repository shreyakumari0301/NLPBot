# Full-Duplex Voice Agent (Call-Center Style)

## What’s Implemented

- **STT (local):** faster-whisper — 16 kHz mono PCM in, text out. Used by `POST /live/audio`.
- **VAD:** webrtcvad — 10/20/30 ms frames, 16-bit PCM. Use in client or backend to detect user speech start (interrupt) and end (finalize).
- **TTS (local):** pyttsx3 (female system voice) or Coqui XTTS when `USE_COQUI_TTS=1`. `GET /live/tts?text=...` returns WAV; `/live/audio` can return `tts_audio_base64`.
- **Brain:** LangChain + OpenAI (or **Ollama** when `USE_OLLAMA=1`, model `OLLAMA_MODEL=mistral`). Conversation history and slot state are in session; LLM decides reply.
- **Interrupt:** Client stops TTS playback when user speaks (browser or VAD); next utterance is sent as new `/live/audio` or `/live/message`. Server always processes the latest transcript (no “resume” state yet).

## Flow

1. Mic → record segment (e.g. 3–5 s or until VAD silence).
2. `POST /live/audio` with `session_id` + audio file (+ `return_tts=true`).
3. Server: STT → `turn(session_id, transcript)` → bot reply; optionally TTS → base64.
4. Client: play TTS (or browser synth); if user talks, stop playback and go to 1.
5. Loop until call ends.

## Env (optional)

- `USE_OLLAMA=1` — use local Ollama (run `ollama run mistral`).
- `OLLAMA_MODEL=mistral` — or `llama3`, `phi3`, etc.
- `OPENAI_API_KEY` — used when Ollama not set.
- `USE_COQUI_TTS=1` — use Coqui XTTS (install `TTS`); else pyttsx3.

## Next (if you want)

- WebSocket: stream audio up, stream TTS chunks down, server stops TTS on “interrupt” message.
- Explicit conversation state machine: bot_speaking / listening / processing; persist “last asked” and “missing slots” for resume.
- Human takeover switch and post-call summary (long-term memory).
