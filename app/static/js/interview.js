// static/js/interview.js

const QUESTIONS = [
  { text: "Расскажите о своем опыте работы с Python.", answerLimitSec: 90 },
  { text: "Какие библиотеки Python вы используете чаще всего и почему?", answerLimitSec: 90 },
  { text: "Опишите задачу, где вы оптимизировали производительность кода.", answerLimitSec: 120 },
];

// Фиксированный лимит ответа: 1 минута (обратный отсчёт)
const ANSWER_LIMIT_SEC = 60;

// Voice Activity Detection (подстрой порог под микрофон)
const VAD_THRESHOLD = 0.03; // 0.02–0.06 обычно
const VAD_HANG_MS = 250;    // задержка "гашения", чтобы не мигало

const timerElement = document.getElementById("timer");
const mainBtn = document.getElementById("main-btn");
const endAnswerBtn = document.getElementById("end-answer-btn");
const nextBtn = document.getElementById("next-btn");
const stopBtn = document.getElementById("stop-btn");

const questionNumberEl = document.getElementById("question-number");
const questionTextEl = document.getElementById("question-text");
const statusEl = document.getElementById("status");
const micIndicator = document.getElementById("mic-indicator");
const recordingsEl = document.getElementById("recordings");

let questionIndex = 0;

// state: idle -> asking -> ready -> recording -> recorded
let state = "idle";

// ===== Mic indicator state (armed = идет запись, speaking = говорит) =====
let micArmed = false;
let micSpeaking = false;

function applyMicIndicator() {
  if (!micIndicator) return;

  if (!micArmed) {
    micIndicator.style.opacity = "0.35";
    micIndicator.classList.remove("speaking");
    return;
  }

  micIndicator.style.opacity = micSpeaking ? "1" : "0.35";
  micIndicator.classList.toggle("speaking", micSpeaking);
}

function setMic(active) {
  micArmed = !!active;
  if (!micArmed) micSpeaking = false;
  applyMicIndicator();
}

function setMicSpeaking(active) {
  micSpeaking = !!active;
  applyMicIndicator();
}

// ===== Timer (countdown) =====
let remainingSec = 0;
let timer = null;

function formatMMSS(totalSec) {
  const safe = Math.max(0, totalSec);
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function updateTimer() {
  if (timerElement) timerElement.textContent = formatMMSS(remainingSec);
}

function setTimerValue(sec) {
  remainingSec = sec;
  updateTimer();
}

function stopTimer() {
  if (timer) clearInterval(timer);
  timer = null;
  remainingSec = 0;
  updateTimer();
}

function startCountdown(limitSec = ANSWER_LIMIT_SEC) {
  if (timer) clearInterval(timer);

  remainingSec = limitSec;
  updateTimer();

  timer = setInterval(() => {
    remainingSec--;
    updateTimer();

    if (remainingSec <= 0) {
      clearInterval(timer);
      timer = null;
      remainingSec = 0;
      updateTimer();

      // Таймаут только во время записи
      if (state === "recording") {
        // Вызов из setInterval — не await, без падения промиса
        finishAnswer("timeout").catch(() => {});
      }
    }
  }, 1000);
}

// ===== UI helpers =====
function setStatus(text) {
  if (statusEl) statusEl.textContent = text || "";
}

function renderQuestion() {
  const q = QUESTIONS[questionIndex];
  if (questionNumberEl) questionNumberEl.textContent = String(questionIndex + 1);
  if (questionTextEl) questionTextEl.textContent = q?.text || "";
}

function setButtons({ mainText, mainEnabled, showEndAnswer, showNext }) {
  if (mainBtn) {
    mainBtn.textContent = mainText;
    mainBtn.disabled = !mainEnabled;
  }
  if (endAnswerBtn) endAnswerBtn.style.display = showEndAnswer ? "inline-block" : "none";
  if (nextBtn) nextBtn.style.display = showNext ? "inline-block" : "none";
}

function speak(text) {
  return new Promise((resolve, reject) => {
    if (!window.speechSynthesis) {
      resolve();
      return;
    }

    window.speechSynthesis.cancel();

    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "ru-RU";
    utter.onend = () => resolve();
    utter.onerror = (e) => reject(e);

    window.speechSynthesis.speak(utter);
  });
}

// ===== Recording =====
let mediaStream = null;
let recorder = null;
let chunks = [];
let currentMimeType = null;

// защита от "старых" onstop после abort/reset
let sessionToken = 0;

// мета текущей записи (объект сохраняется в замыкании onstop)
let currentRecordingMeta = null; // { qIndex, session, endedBy: "manual"|"timeout"|null }

function pickSupportedMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  for (const t of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
  }
  return null;
}

async function ensureMic() {
  if (mediaStream) return mediaStream;
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  return mediaStream;
}

async function startRecording() {
  await ensureMic();
  chunks = [];

  const meta = currentRecordingMeta; // замыкание

  currentMimeType = pickSupportedMimeType();
  recorder = currentMimeType
    ? new MediaRecorder(mediaStream, { mimeType: currentMimeType })
    : new MediaRecorder(mediaStream);

  recorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };

  recorder.onstop = () => {
    // если сессия уже сброшена — игнорируем
    if (!meta || meta.session !== sessionToken) return;

    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
    addRecording(meta.qIndex, blob, { endedBy: meta.endedBy || "manual" });
  };

  recorder.start();
}

function stopRecording() {
  if (recorder && recorder.state === "recording") {
    recorder.stop();
  }
}

function stopRecordingAsync() {
  return new Promise((resolve) => {
    if (!recorder || recorder.state !== "recording") {
      resolve();
      return;
    }
    recorder.addEventListener("stop", () => resolve(), { once: true });
    recorder.stop();
  });
}

function addRecording(qIndex, blob, meta = {}) {
  if (!recordingsEl) return;

  const url = URL.createObjectURL(blob);

  const card = document.createElement("div");
  card.className = "mt-3 p-3 border rounded";

  const title = document.createElement("div");
  const timeoutNote = meta.endedBy === "timeout" ? " — <em>время кончилось</em>" : "";
  title.innerHTML = `<strong>Ответ на вопрос №${qIndex + 1}</strong>${timeoutNote}`;
  card.appendChild(title);

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.src = url;
  audio.className = "mt-2 w-100";
  card.appendChild(audio);

  const a = document.createElement("a");
  a.href = url;
  a.download = `answer_q${qIndex + 1}.${blob.type.includes("ogg") ? "ogg" : "webm"}`;
  a.textContent = "Скачать запись";
  a.className = "d-inline-block mt-2";
  card.appendChild(a);

  recordingsEl.appendChild(card);
}

// ===== Voice Activity Detection (Web Audio API) =====
const VAD = {
  audioCtx: null,
  analyser: null,
  source: null,
  data: null,
  rafId: null,
  speakingUntil: 0,
};

async function startVoiceActivity() {
  if (VAD.rafId) return; // уже запущено
  await ensureMic();

  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;

  if (!VAD.audioCtx) VAD.audioCtx = new AC();
  if (VAD.audioCtx.state === "suspended") {
    try {
      await VAD.audioCtx.resume();
    } catch (_) {}
  }

  // чистим старые узлы
  try { VAD.source?.disconnect(); } catch (_) {}
  try { VAD.analyser?.disconnect(); } catch (_) {}

  VAD.source = VAD.audioCtx.createMediaStreamSource(mediaStream);
  VAD.analyser = VAD.audioCtx.createAnalyser();
  VAD.analyser.fftSize = 1024;
  VAD.data = new Uint8Array(VAD.analyser.fftSize);

  VAD.source.connect(VAD.analyser);

  const tick = () => {
    if (!VAD.analyser || !VAD.data) return;

    VAD.analyser.getByteTimeDomainData(VAD.data);

    // RMS по тайм-домену
    let sum = 0;
    for (let i = 0; i < VAD.data.length; i++) {
      const x = (VAD.data[i] - 128) / 128; // [-1..1]
      sum += x * x;
    }
    const rms = Math.sqrt(sum / VAD.data.length);

    const now = performance.now();
    if (rms >= VAD_THRESHOLD) {
      VAD.speakingUntil = now + VAD_HANG_MS;
    }

    const speaking = now < VAD.speakingUntil;

    // Подсветка имеет смысл только во время записи
    if (state === "recording") setMicSpeaking(speaking);
    else setMicSpeaking(false);

    VAD.rafId = requestAnimationFrame(tick);
  };

  tick();
}

function stopVoiceActivity() {
  if (VAD.rafId) cancelAnimationFrame(VAD.rafId);
  VAD.rafId = null;

  setMicSpeaking(false);

  try { VAD.source?.disconnect(); } catch (_) {}
  try { VAD.analyser?.disconnect(); } catch (_) {}

  VAD.source = null;
  VAD.analyser = null;
  VAD.data = null;
  VAD.speakingUntil = 0;
}

// ===== Flow =====
async function startInterview() {
  // новая "сессия" — защищаемся от старых onstop
  sessionToken++;

  // стопаем все активные процессы
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  stopTimer();
  stopVoiceActivity();
  setMic(false);

  questionIndex = 0;
  renderQuestion();

  setStatus("Готово. Нажмите «Начать», чтобы услышать вопрос.");
  setTimerValue(ANSWER_LIMIT_SEC);

  state = "idle";
  setButtons({ mainText: "Начать", mainEnabled: true, showEndAnswer: false, showNext: false });
}

async function askCurrentQuestion() {
  const q = QUESTIONS[questionIndex];
  if (!q) return;

  state = "asking";
  setMic(false);
  stopVoiceActivity();
  stopTimer();
  setTimerValue(ANSWER_LIMIT_SEC);

  setStatus("Озвучиваю вопрос…");
  setButtons({ mainText: "Озвучивается…", mainEnabled: false, showEndAnswer: false, showNext: false });

  try {
    await speak(q.text);
  } catch (_) {}

  state = "ready";
  setStatus("Вопрос завершён. Нажмите «Ответить», чтобы начать запись.");
  setButtons({ mainText: "Ответить", mainEnabled: true, showEndAnswer: false, showNext: false });

  // превью таймера (01:00)
  stopTimer();
  setTimerValue(ANSWER_LIMIT_SEC);
}

async function beginAnswer() {
  state = "recording";
  setStatus("Запись ответа идёт…");
  setMic(true);
  setButtons({ mainText: "Идёт запись…", mainEnabled: false, showEndAnswer: true, showNext: false });

  // мета для текущей записи
  currentRecordingMeta = { qIndex: questionIndex, session: sessionToken, endedBy: null };

  startCountdown(ANSWER_LIMIT_SEC);

  try {
    await startVoiceActivity();
    await startRecording();
  } catch (e) {
    // откат в ready
    state = "ready";
    stopVoiceActivity();
    setMic(false);

    stopTimer();
    setTimerValue(ANSWER_LIMIT_SEC);

    setStatus("Не удалось получить доступ к микрофону. Разрешите доступ и попробуйте снова.");
    setButtons({ mainText: "Ответить", mainEnabled: true, showEndAnswer: false, showNext: false });

    console.error(e);
    setStatus(`Микрофон недоступен: ${e.name} — ${e.message || ""}`);
  }
}

async function finishAnswer(reason = "manual") {
  if (state !== "recording") return;

  // отметка причины завершения
  if (currentRecordingMeta) currentRecordingMeta.endedBy = reason;

  stopTimer();
  stopVoiceActivity();
  setMic(false);

  // дождаться добавления карточки (onstop)
  await stopRecordingAsync();

  state = "recorded";

  if (reason === "timeout") {
    setStatus("Время вышло — перехожу к следующему вопросу.");
    setButtons({ mainText: "Ответить", mainEnabled: false, showEndAnswer: false, showNext: false });

    nextQuestion();
    return;
  }

  setStatus("Ответ сохранён. Можно перейти к следующему вопросу.");
  setButtons({ mainText: "Ответить", mainEnabled: false, showEndAnswer: false, showNext: true });
}

function nextQuestion() {
  if (questionIndex < QUESTIONS.length - 1) {
    questionIndex++;
    renderQuestion();
    askCurrentQuestion();
    return;
  }

  state = "idle";
  setStatus("Интервью завершено. Записи ответов ниже.");
  stopTimer();
  setTimerValue(ANSWER_LIMIT_SEC);
  stopVoiceActivity();
  setMic(false);

  setButtons({ mainText: "Начать заново", mainEnabled: true, showEndAnswer: false, showNext: false });
}

function abortSession() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();

  // если шла запись — остановим, но "старые" onstop будут проигнорированы (sessionToken)
  stopRecording();

  stopTimer();
  stopVoiceActivity();
  setMic(false);

  if (recordingsEl) recordingsEl.innerHTML = "";

  startInterview();
}

// ===== Events =====
mainBtn?.addEventListener("click", async () => {
  const txt = (mainBtn.textContent || "").toLowerCase();

  // обработаем "заново" раньше state==="idle"
  if (txt.includes("заново")) {
    if (recordingsEl) recordingsEl.innerHTML = "";
    await startInterview();
    return;
  }

  if (state === "idle") {
    await askCurrentQuestion();
    return;
  }

  if (state === "ready") {
    await beginAnswer();
    return;
  }
});

endAnswerBtn?.addEventListener("click", () => {
  finishAnswer("manual").catch(() => {});
});

nextBtn?.addEventListener("click", () => {
  nextQuestion();
});

stopBtn?.addEventListener("click", () => {
  if (confirm("Вы уверены, что хотите прервать сессию?")) abortSession();
});

// init
startInterview();
