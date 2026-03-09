const CONFIG = {
  TOTAL_LIMIT_SEC: 180,
  VAD_THRESHOLD: 0.03,
  VAD_HANG_MS: 250,
  TIMER_TICK_MS: 1000,
};

const QUESTIONS = window.INTERVIEW_DATA?.questions || [];
const SESSION_ID = window.INTERVIEW_DATA?.sessionId || null;
const feedbackPanel = document.getElementById("feedback-panel");
const feedbackScoreEl = document.getElementById("feedback-score");
const feedbackVerdictEl = document.getElementById("feedback-verdict");
const feedbackCriteriaEl = document.getElementById("feedback-criteria");

const timerSection = document.querySelector(".timer-section");
const timerElement = document.getElementById("timer");

const mainBtn = document.getElementById("main-btn");
const nextBtn = document.getElementById("next-btn");
const stopBtn = document.getElementById("stop-btn");

const questionNumberEl = document.getElementById("question-number");
const questionTotalEl = document.getElementById("question-total");
const questionTextEl = document.getElementById("question-text");

const statusEl = document.getElementById("status");
const micIndicator = document.getElementById("mic-indicator");
const recordingsEl = document.getElementById("recordings");


let state = "idle";
let questionIndex = 0;
let recordedDurationSec = 0;
let sessionStartTs = null;
let currentAnswerStartTs = null;
let questionSegments = [];

let mediaStream = null;
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

function startGlobalCountdown() {
  if (timer) clearInterval(timer);

  remainingSec = CONFIG.TOTAL_LIMIT_SEC;
  updateTimer();

  timer = setInterval(() => {
    remainingSec--;
    updateTimer();

    if (remainingSec <= 0) {
      clearInterval(timer);
      timer = null;
      remainingSec = 0;
      updateTimer();
      finishInterviewByTimeout();
    }
  }, CONFIG.TIMER_TICK_MS);
}

function stopTimer() {
  if (timer) clearInterval(timer);
  timer = null;
}

function hideInterviewUI() {
  if (timerSection) timerSection.style.display = "none";
}

function showInterviewUI() {
  if (timerSection) timerSection.style.display = "block";
}

function setStatus(text) {
  if (statusEl) statusEl.textContent = text || "";
}

function resetFeedback() {
  if (feedbackPanel) feedbackPanel.style.display = "none";
  if (feedbackScoreEl) feedbackScoreEl.textContent = "";
  if (feedbackVerdictEl) feedbackVerdictEl.textContent = "";
  if (feedbackCriteriaEl) feedbackCriteriaEl.innerHTML = "";
}

function renderFeedback(feedback) {
  if (!feedback || !feedbackPanel) return;

  feedbackPanel.style.display = "block";

  if (feedbackScoreEl) {
    feedbackScoreEl.textContent = Number(feedback.score || 0).toFixed(2);
  }

  if (feedbackVerdictEl) {
    feedbackVerdictEl.textContent = feedback.verdict || "";
  }

  if (feedbackCriteriaEl) {
    feedbackCriteriaEl.innerHTML = "";

    const list = document.createElement("ul");
    list.className = "mb-0";

    for (const [name, value] of Object.entries(feedback.criteria_results || {})) {
      const item = document.createElement("li");
      const resultValue = Number(value?.result || 0).toFixed(2);
      const verdict = value?.verdict ? ` — ${value.verdict}` : "";
      item.textContent = `${name}: ${resultValue}${verdict}`;
      list.appendChild(item);
    }

    feedbackCriteriaEl.appendChild(list);
  }
}

function setButtons({ mainText, mainEnabled, showNext }) {
  if (mainBtn) {
    mainBtn.textContent = mainText;
    mainBtn.disabled = !mainEnabled;
  }
  if (nextBtn) nextBtn.style.display = showNext ? "inline-block" : "none";
}

function renderQuestion() {
  const q = QUESTIONS[questionIndex];
  if (!q) return;

  if (questionNumberEl) questionNumberEl.textContent = String(questionIndex + 1);
  if (questionTextEl) questionTextEl.textContent = q.text || "";

  if (nextBtn) {
    nextBtn.textContent =
      questionIndex === QUESTIONS.length - 1 ? "Закончить" : "Следующий вопрос";
  }
}

function speak(text) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) return resolve();
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "ru-RU";
    utter.onend = resolve;
    utter.onerror = resolve;
    window.speechSynthesis.speak(utter);
  });
}

let sessionRecorder = null;
let fullSessionChunks = [];

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

async function startSessionRecording() {
  await ensureMic();
  fullSessionChunks = [];
  sessionStartTs = performance.now();
  questionSegments = [];

  const mimeType = pickSupportedMimeType();
  sessionRecorder = mimeType
    ? new MediaRecorder(mediaStream, { mimeType })
    : new MediaRecorder(mediaStream);

  sessionRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) fullSessionChunks.push(e.data);
  };

  sessionRecorder.start();

  startMicIndicator();
}

function stopSessionRecording() {
  if (!sessionRecorder) return;

  sessionRecorder.onstop = () => {
    const blob = new Blob(fullSessionChunks, { type: "audio/webm" });
    addFullSessionRecording(blob);
    sendSessionToBackend(blob);
  };

  sessionRecorder.stop();
}

let vadInterval = null;
function startMicIndicator() {
  if (!mediaStream) return;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  const audioCtx = new AC();
  const source = audioCtx.createMediaStreamSource(mediaStream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const data = new Uint8Array(analyser.fftSize);

  setMic(true);

  vadInterval = setInterval(() => {
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      const x = (data[i] - 128) / 128;
      sum += x * x;
    }
    const rms = Math.sqrt(sum / data.length);
    setMicSpeaking(rms > CONFIG.VAD_THRESHOLD);
  }, 50);
}

function stopMicIndicator() {
  if (vadInterval) clearInterval(vadInterval);
  vadInterval = null;
  setMicSpeaking(false);
  setMic(false);
}

function closeCurrentAnswer() {
  if (currentAnswerStartTs == null) return;
  const now = performance.now();
  const q = QUESTIONS[questionIndex];
  questionSegments.push({
    question_id: q?.id || q?._id || null,
    order: questionIndex,
    start: (currentAnswerStartTs - sessionStartTs) / 1000,
    end: (now - sessionStartTs) / 1000,
  });
  currentAnswerStartTs = null;
}

async function startInterview() {
  showInterviewUI();
  recordingsEl.innerHTML = "";
  resetFeedback();
  recordedDurationSec = 0;
  questionIndex = 0;
  state = "running";

  if (questionTotalEl) questionTotalEl.textContent = QUESTIONS.length;

  renderQuestion();
  setStatus("Интервью началось");

  setButtons({ mainText: "Озвучить вопрос", mainEnabled: true, showNext: false });

  await startSessionRecording();
  startGlobalCountdown();
}

async function askQuestion() {
  const q = QUESTIONS[questionIndex];
  if (!q) return;

  setStatus("Озвучиваю вопрос…");
  setButtons({ mainText: "Озвучивается…", mainEnabled: false, showNext: false });

  await speak(q.text);

  currentAnswerStartTs = performance.now();

  setStatus("Говорите ответ");
  setButtons({ mainText: "Озвучить вопрос", mainEnabled: false, showNext: true });
}

function nextQuestion() {
  closeCurrentAnswer();
  if (questionIndex < QUESTIONS.length - 1) {
    questionIndex++;
    renderQuestion();
    askQuestion();
    return;
  }
  finishInterview();
}

function finishInterview() {
  closeCurrentAnswer();

  recordedDurationSec = sessionStartTs == null
    ? 0
    : (performance.now() - sessionStartTs) / 1000;

  state = "finished";
  stopTimer();
  stopSessionRecording();
  stopMicIndicator();

  hideInterviewUI();
  setStatus("Интервью завершено");

  setButtons({ mainText: "Начать заново", mainEnabled: true, showNext: false });
}

function finishInterviewByTimeout() {
  setStatus("Время интервью вышло");
  finishInterview();
}

function addFullSessionRecording(blob) {
  const url = URL.createObjectURL(blob);
  const card = document.createElement("div");
  card.className = "mt-3 p-3 border rounded";
  card.innerHTML = `
    <strong>Запись всей тренировки</strong>
    <audio controls src="${url}" class="mt-2 w-100"></audio>
    <a href="${url}" download="interview_full.webm" class="d-block mt-2">
      Скачать запись
    </a>
  `;
  recordingsEl.appendChild(card);
}

async function sendSessionToBackend(blob) {
  if (!SESSION_ID) return;

  const form = new FormData();
  form.append("audio", blob, "interview_full.webm");
  form.append("session_id", SESSION_ID);
  form.append("segments", JSON.stringify(questionSegments));
  form.append("duration", String(recordedDurationSec.toFixed(2)));

  try {
    const resp = await fetch("/api/interview/recording", {
      method: "POST",
      body: form
    });

    const data = await resp.json();

    if (!resp.ok) {
      console.warn("Ошибка отправки записи:", resp.status, data);
      setStatus(data?.error || "Не удалось сохранить интервью");
      return;
    }

    if (data.results_url) {
      window.location.href = data.results_url;
      return;
    }

    setStatus("Интервью завершено, но не удалось открыть страницу результатов");
  } catch (err) {
    console.error("Ошибка при fetch:", err);
    setStatus("Ошибка при отправке интервью");
  }
}


mainBtn?.addEventListener("click", async () => {
  if (state === "idle" || state === "finished") {
    await startInterview();
    return;
  }
  if (state === "running") {
    await askQuestion();
  }
});

nextBtn?.addEventListener("click", nextQuestion);
stopBtn?.addEventListener("click", finishInterview);


hideInterviewUI();
setStatus("Нажмите «Начать», чтобы начать интервью");
