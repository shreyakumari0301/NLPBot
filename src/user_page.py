"""User-facing first page: what we offer → get in touch (details + call or chat) → chat."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

USER_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>XYZ Animations — Animation & Video Production</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; min-height: 100vh; background: #0f1419; color: #e7e9ea; }
    .screen { display: none; min-height: 100vh; flex-direction: column; padding: 1.5rem; max-width: 42rem; margin: 0 auto; }
    .screen.visible { display: flex; }
    h1 { font-size: 1.75rem; margin: 0 0 1rem; }
    .lead { font-size: 1.1rem; color: #8b98a5; margin-bottom: 1.5rem; line-height: 1.5; }
    .offers { list-style: none; padding: 0; margin: 0 0 2rem; }
    .offers li { padding: 0.5rem 0; padding-left: 1.25rem; position: relative; }
    .offers li::before { content: ''; position: absolute; left: 0; top: 0.75rem; width: 6px; height: 6px; border-radius: 50%; background: #1d9bf0; }
    .cta { display: inline-block; padding: 0.75rem 1.5rem; background: #1d9bf0; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; font-size: 1rem; }
    .cta:hover { background: #1a8cd8; }
    .contact-form label { display: block; margin-top: 1rem; margin-bottom: 0.25rem; font-size: 0.9rem; }
    .contact-form input, .contact-form select { width: 100%; padding: 0.6rem; border: 1px solid #2f3336; border-radius: 6px; background: #202327; color: #e7e9ea; font-size: 1rem; }
    .contact-form input::placeholder { color: #71767b; }
    .choice-row { display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; }
    .choice-btn { flex: 1; min-width: 140px; padding: 1rem; border: 2px solid #2f3336; border-radius: 8px; background: transparent; color: #e7e9ea; font-size: 1rem; cursor: pointer; text-align: center; }
    .choice-btn:hover { border-color: #1d9bf0; background: #1d9bf01f; }
    .choice-btn strong { display: block; margin-bottom: 0.25rem; }
    .back { color: #8b98a5; font-size: 0.9rem; margin-bottom: 1rem; cursor: pointer; }
    .back:hover { color: #e7e9ea; }
    .chat-screen .header { padding: 0.5rem 0; font-weight: 600; margin-bottom: 0.5rem; }
    .chat { flex: 1; overflow-y: auto; padding: 0.5rem 0; display: flex; flex-direction: column; gap: 0.75rem; min-height: 200px; }
    .msg { max-width: 85%; padding: 0.6rem 0.9rem; border-radius: 1rem; line-height: 1.4; }
    .msg.bot { align-self: flex-start; background: #1d9bf0; color: #fff; border-bottom-left-radius: 0.25rem; }
    .msg.user { align-self: flex-end; background: #2f3336; border-bottom-right-radius: 0.25rem; }
    .msg-form { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
    .msg-form input { flex: 1; padding: 0.6rem 0.9rem; border: 1px solid #2f3336; border-radius: 999px; background: #202327; color: #e7e9ea; font-size: 1rem; }
    .msg-form button { padding: 0.6rem 1.2rem; border: none; border-radius: 999px; background: #1d9bf0; color: #fff; font-weight: 600; cursor: pointer; }
    .msg-form button:disabled { opacity: 0.6; cursor: not-allowed; }
    #status { font-size: 0.8rem; color: #71767b; }
    .call-confirm { padding: 1rem; background: #16213e; border-radius: 8px; margin-bottom: 1rem; }
    .call-confirm p { margin: 0 0 0.5rem; }
    .voice-bar { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; padding: 0.75rem; background: #16213e; border-radius: 8px; }
    .voice-bar .mic-btn { width: 56px; height: 56px; border-radius: 50%; border: none; background: #1d9bf0; color: #fff; cursor: pointer; font-size: 1.5rem; display: flex; align-items: center; justify-content: center; }
    .voice-bar .mic-btn:hover { background: #1a8cd8; }
    .voice-bar .mic-btn.listening { background: #e74c3c; animation: pulse 1s ease infinite; }
    @keyframes pulse { 50% { opacity: 0.8; } }
    .voice-bar .voice-label { font-size: 0.9rem; color: #8b98a5; }
    .call-screen { align-items: center; justify-content: center; text-align: center; padding: 2rem; }
    .call-screen .call-avatar { width: 120px; height: 120px; border-radius: 50%; background: #1d9bf0; margin: 0 auto 1.5rem; display: flex; align-items: center; justify-content: center; font-size: 3rem; }
    .call-screen .call-title { font-size: 1.25rem; margin-bottom: 0.25rem; }
    .call-screen .call-status { font-size: 1rem; color: #8b98a5; margin-bottom: 2rem; min-height: 1.5em; }
    .call-screen .call-status.listening { color: #2ecc71; }
    .call-screen .call-status.speaking { color: #1d9bf0; }
    .call-screen .end-call { padding: 0.75rem 2rem; border-radius: 999px; border: none; background: #e74c3c; color: #fff; font-weight: 600; cursor: pointer; margin-top: 1rem; }
    .call-screen .end-call:hover { background: #c0392b; }
    .call-screen .no-voice { color: #e74c3c; margin-top: 1rem; font-size: 0.9rem; }
  </style>
</head>
<body>
  <div id="landing" class="screen visible">
    <h1>XYZ Animations</h1>
    <p class="lead">We create 2D & 3D animation and video content for brands, films, and campaigns.</p>
    <ul class="offers">
      <li>2D & 3D animation (short films, explainers, ads)</li>
      <li>Promo videos and motion graphics</li>
      <li>Custom character design and storyboarding</li>
      <li>From concept to delivery — we handle the full pipeline</li>
    </ul>
    <button type="button" class="cta" id="btnGetInTouch">Get in touch</button>
  </div>

  <div id="contact" class="screen">
    <a class="back" id="backFromContact">&larr; Back</a>
    <h1>Get in touch</h1>
    <p class="lead">Share a few details and how you’d like to discuss.</p>
    <form class="contact-form" id="contactForm">
      <label for="name">Name</label>
      <input type="text" id="name" name="name" placeholder="Your name" required />
      <label for="phone">Phone</label>
      <input type="tel" id="phone" name="phone" placeholder="Phone number" />
      <label for="interest">What do you need?</label>
      <input type="text" id="interest" name="interest" placeholder="e.g. short film, ad, quote" />
      <label>How would you like to discuss?</label>
      <div class="choice-row">
        <button type="button" class="choice-btn" id="choiceCall"><strong>Call me</strong> Request a callback</button>
        <button type="button" class="choice-btn" id="choiceChat"><strong>Chat now</strong> Talk with us live</button>
      </div>
    </form>
  </div>

  <div id="callConfirm" class="screen">
    <a class="back" id="backFromCall">&larr; Back</a>
    <h1>We’ll call you</h1>
    <div class="call-confirm">
      <p>Thanks, <span id="callName"></span>. We’ll call you shortly at <strong id="callPhone"></strong>.</p>
      <p>You can also start a chat below if you prefer.</p>
    </div>
    <button type="button" class="cta" id="startChatAfterCall">Start chat instead</button>
  </div>

  <div id="callScreen" class="screen call-screen">
    <a class="back" id="backFromCallScreen" style="position:absolute;top:1rem;left:1rem;">&larr; End call</a>
    <div class="call-avatar">&#128100;</div>
    <div class="call-title">Live call with Mira</div>
    <div class="call-status" id="callStatus">Connecting…</div>
    <div class="call-you-said" id="youSaid" style="display:none; font-size:0.85rem; color:#8b98a5; margin-top:0.5rem; min-height:1.2em;">You said: <span id="youSaidText"></span></div>
    <p style="font-size:0.85rem; color:#71767b; max-width:22rem;">Use headphones so you can talk and hear. You can interrupt anytime — just like a real call.</p>
    <p style="font-size:0.8rem; color:#8b98a5; max-width:22rem; margin-top:0.5rem;">If I don’t respond: allow the mic in the browser, pick your <strong>microphone</strong> (not system/speaker) in browser or system sound settings, or try an external mic or headset.</p>
    <button type="button" class="end-call" id="endCallBtn">End call</button>
    <div class="no-voice" id="noVoiceMsg" style="display:none;">Voice not supported in this browser.</div>
  </div>

  <script>
    const landing = document.getElementById('landing');
    const contact = document.getElementById('contact');
    const callConfirm = document.getElementById('callConfirm');
    const callScreen = document.getElementById('callScreen');
    const callStatus = document.getElementById('callStatus');
    const endCallBtn = document.getElementById('endCallBtn');
    const noVoiceMsg = document.getElementById('noVoiceMsg');
    let sessionId = null;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    const synth = window.speechSynthesis;
    let femaleVoice = null;
    function getFemaleVoice() {
      const voices = synth.getVoices();
      if (femaleVoice) return femaleVoice;
      femaleVoice = voices.find(v => v.lang.startsWith('en') && /female|zira|samantha|victoria|kate|anna|karen|moira|susan|google uk english female|microsoft zira/i.test(v.name))
        || voices.find(v => v.lang.startsWith('en'));
      return femaleVoice;
    }
    synth.onvoiceschanged = () => getFemaleVoice();
    getFemaleVoice();
    const STATE = { CONNECTING: 0, LISTENING: 1, PROCESSING: 2, SPEAKING: 3 };
    let callState = STATE.CONNECTING;

    function show(el) {
      [landing, contact, callConfirm, callScreen].forEach(s => s && s.classList.remove('visible'));
      if (el) el.classList.add('visible');
    }

    document.getElementById('btnGetInTouch').onclick = () => show(contact);
    document.getElementById('backFromContact').onclick = () => show(landing);
    document.getElementById('backFromCall').onclick = () => show(contact);
    document.getElementById('backFromCallScreen').onclick = endCall;
    endCallBtn.onclick = endCall;

    document.getElementById('choiceCall').onclick = () => {
      const name = document.getElementById('name').value.trim() || 'there';
      const phone = document.getElementById('phone').value.trim() || 'your number';
      document.getElementById('callName').textContent = name;
      document.getElementById('callPhone').textContent = phone;
      show(callConfirm);
    };

    document.getElementById('choiceChat').onclick = () => {
      show(callScreen);
      if (!sessionId) startCall();
    };
    document.getElementById('startChatAfterCall').onclick = () => {
      show(callScreen);
      if (!sessionId) startCall();
    };

    function setStatus(text, className) {
      if (!callStatus) return;
      callStatus.textContent = text;
      callStatus.className = 'call-status' + (className ? ' ' + className : '');
    }

    function stopRecognition() {
      try { if (recognition) recognition.stop(); } catch (e) {}
    }

    function startListening() {
      if (!recognition || callState === STATE.PROCESSING) return;
      try {
        recognition.start();
        callState = STATE.LISTENING;
        setStatus('Listening… speak now.', 'listening');
      } catch (e) {}
    }

    let ttsStartTime = 0;
    const GRACE_MS = 1200;

    function speak(text, onEnd) {
      if (!synth || !text) { if (onEnd) onEnd(); return; }
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const voice = getFemaleVoice();
      if (voice) u.voice = voice;
      u.rate = 0.9;
      u.pitch = 1.05;
      ttsStartTime = Date.now();
      u.onend = () => {
        setStatus('Mira is speaking…', 'speaking');
        setTimeout(function() { if (onEnd) onEnd(); }, 300);
      };
      u.onerror = () => { if (onEnd) onEnd(); };
      synth.speak(u);
      callState = STATE.SPEAKING;
      setStatus('Mira is speaking…', 'speaking');
      startListening();
    }

    function setYouSaid(text) {
      const el = document.getElementById('youSaid');
      const txt = document.getElementById('youSaidText');
      if (el && txt) {
        txt.textContent = text || '';
        el.style.display = text ? 'block' : 'none';
      }
    }

    function handleUserSpeech(transcript) {
      if (!sessionId) return;
      const t = (transcript || '').trim();
      setYouSaid(t || '(no words captured)');
      if (!t) return;
      if (callState === STATE.SPEAKING && (Date.now() - ttsStartTime) < GRACE_MS) return;
      if (callState === STATE.SPEAKING) synth.cancel();
      callState = STATE.PROCESSING;
      setStatus('Thinking…');
      stopRecognition();
      fetch('/live/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, user_message: t })
      })
        .then(r => r.json())
        .then(d => {
          if (d.bot_reply) {
            speak(d.bot_reply, () => { startListening(); });
          } else {
            startListening();
          }
        })
        .catch(() => {
          speak('Sorry, something went wrong. Try again.', () => { startListening(); });
        });
    }

    async function startCall() {
      setStatus('Connecting…');
      try {
        const r = await fetch('/live/start', { method: 'POST' });
        const d = await r.json();
        sessionId = d.session_id;
        if (!SpeechRecognition) {
          setStatus('Voice not supported.');
          noVoiceMsg.style.display = 'block';
          return;
        }
        if (d.bot_reply) {
          speak(d.bot_reply, () => { startListening(); });
        } else {
          startListening();
        }
      } catch (e) {
        setStatus('Connection failed. End call and try again.');
      }
    }

    function endCall() {
      callState = STATE.CONNECTING;
      stopRecognition();
      synth.cancel();
      sessionId = null;
      show(contact);
    }

    if (SpeechRecognition) {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-IN';
      recognition.onresult = (e) => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) {
            const t = e.results[i][0].transcript;
            if (t && t.trim()) handleUserSpeech(t.trim());
            break;
          }
        }
      };
      recognition.onend = () => {
        if (callState === STATE.LISTENING || callState === STATE.SPEAKING) {
          try { recognition.start(); } catch (x) {}
        }
      };
      recognition.onerror = (e) => {
        if (e.error !== 'aborted' && e.error !== 'no-speech' && callState === STATE.LISTENING) setStatus('Could not hear. Listening again…', 'listening');
      };
    }
  </script>
</body>
</html>
"""

router = APIRouter(tags=["user"])


@router.get("/", response_class=HTMLResponse)
def user_page():
    """First page: what we offer → get in touch (details + call or chat) → chat."""
    return USER_PAGE_HTML
