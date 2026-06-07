document.addEventListener("DOMContentLoaded", () => {
  const CONFIG = {
    DEFAULT_TOTAL_LIMIT_SEC: 180,
    totalLimitSec: 180,
    VAD_THRESHOLD: 0.03,
    VAD_HANG_MS: 250,
    TIMER_TICK_MS: 1000,
  };

  const API = {
    SESSION_DATA_URL: "/api/interview/session-data/",
    RECORDING_URL: "/api/interview/recording",
    RESEARCH_EVENT_URL: "/api/interview/research-event/",
  };

  const feedbackPanel = document.getElementById("feedback-panel");
  const feedbackScoreEl = document.getElementById("feedback-score");
  const feedbackVerdictEl = document.getElementById("feedback-verdict");
  const feedbackCriteriaEl = document.getElementById("feedback-criteria");

  const interviewInfo = document.getElementById("interview-info");
  const timerElement = document.getElementById("timer");
  const mainBtn = document.getElementById("main-btn");
  const nextBtn = document.getElementById("next-btn");
  const questionNumberEl = document.getElementById("question-number");
  const questionTotalEl = document.getElementById("question-total");
  const statusEl = document.getElementById("status");
  const micIndicator = document.getElementById("mic-indicator");
  const pageRoot = document.querySelector(".interview-container");
  const avatarVideo = document.getElementById("question-avatar-video");

  function normalizePositiveInt(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  const bootstrapTimerMin = normalizePositiveInt(pageRoot?.dataset?.sessionTimerMinutes, 0);
  if (bootstrapTimerMin > 0) CONFIG.totalLimitSec = bootstrapTimerMin * 60;

  let questions = [];
  let dataLoaded = false;
  let state = "idle";
  let questionIndex = 0;
  let recordedDurationSec = 0;
  let sessionStartTs = null;
  let currentAnswerStartTs = null;
  let questionSegments = [];

  let mediaStream = null;
  let micArmed = false;
  let micSpeaking = false;

  let currentAnswerTranscriptFinalParts = [];
  let currentAnswerTranscriptInterimByIndex = new Map();
  let currentAnswerPauses = [];
  let currentPauseCandidateTs = null;
  let currentPauseStartTs = null;

  let recognition = null;
  let recognitionActive = false;
  let recognitionShouldRun = false;
  let recognitionStopResolver = null;

  function getCurrentQuestion() { return questions[questionIndex] || null; }

  function logResearchEvent(event, meta = {}) {
    fetch(API.RESEARCH_EVENT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ event, meta }),
    }).catch(() => {});
  }

  // --- Video playback ---

  function playQuestionVideo(qIndex) {
    return new Promise((resolve) => {
      const q = questions[qIndex];
      if (!q || !q.avatar_video_url || !avatarVideo) return resolve();

      let resolved = false;
      function done() {
        if (resolved) return;
        resolved = true;
        avatarVideo.onended = null;
        avatarVideo.onerror = null;
        avatarVideo.onloadeddata = null;
        resolve();
      }

      avatarVideo.onended = null;
      avatarVideo.onerror = null;
      avatarVideo.onloadeddata = null;
      avatarVideo.pause();

      avatarVideo.style.display = "block";
      avatarVideo.onended = done;
      avatarVideo.onerror = done;

      avatarVideo.onloadeddata = () => {
        avatarVideo.onloadeddata = null;
        avatarVideo.play().catch(done);
      };

      avatarVideo.src = q.avatar_video_url;
      avatarVideo.load();
    });
  }

  // --- Mic ---

  function applyMicIndicator() {
    if (!micIndicator) return;
    if (!micArmed) { micIndicator.style.opacity = "0.35"; micIndicator.classList.remove("speaking"); return; }
    micIndicator.style.opacity = micSpeaking ? "1" : "0.35";
    micIndicator.classList.toggle("speaking", micSpeaking);
  }
  function setMic(a) { micArmed = !!a; if (!micArmed) micSpeaking = false; applyMicIndicator(); }
  function setMicSpeaking(a) { micSpeaking = !!a; applyMicIndicator(); }

  // --- Speech recognition ---

  function getSpeechRecognitionCtor() { return window.SpeechRecognition || window.webkitSpeechRecognition || null; }

  function ensureSpeechRecognition() {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return null;
    if (recognition) return recognition;
    recognition = new Ctor();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      if (currentAnswerStartTs == null) return;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i], t = r[0]?.transcript?.trim();
        if (!t) continue;
        if (r.isFinal) { currentAnswerTranscriptFinalParts.push(t); currentAnswerTranscriptInterimByIndex.delete(i); }
        else currentAnswerTranscriptInterimByIndex.set(i, t);
      }
    };
    recognition.onerror = () => {};
    recognition.onend = () => {
      recognitionActive = false;
      if (recognitionStopResolver) { const r = recognitionStopResolver; recognitionStopResolver = null; r(); }
      if (!recognitionShouldRun || state !== "running" || currentAnswerStartTs == null) return;
      try { recognition.start(); recognitionActive = true; } catch {}
    };
    return recognition;
  }

  function resetAnswerSpeechMetrics() {
    currentAnswerTranscriptFinalParts = [];
    currentAnswerTranscriptInterimByIndex = new Map();
    currentAnswerPauses = [];
    currentPauseCandidateTs = null;
    currentPauseStartTs = null;
  }

  function buildCurrentAnswerTranscript() {
    const interim = Array.from(currentAnswerTranscriptInterimByIndex.entries()).sort((a,b) => a[0]-b[0]).map(([,v]) => v);
    return [...currentAnswerTranscriptFinalParts, ...interim].join(" ").replace(/\s+/g, " ").trim();
  }

  function startAnswerSpeechCapture() {
    resetAnswerSpeechMetrics();
    currentPauseCandidateTs = performance.now();
    recognitionShouldRun = true;
    const sr = ensureSpeechRecognition();
    if (!sr || recognitionActive) return;
    try { sr.start(); recognitionActive = true; } catch {}
  }

  function stopAnswerSpeechCapture() {
    recognitionShouldRun = false;
    if (!recognition || !recognitionActive) return Promise.resolve();
    return new Promise((resolve) => {
      let tid = null;
      const done = () => { if (tid) clearTimeout(tid); recognitionStopResolver = null; resolve(); };
      recognitionStopResolver = done;
      tid = setTimeout(() => { recognitionActive = false; done(); }, 800);
      try { recognition.stop(); } catch { recognitionActive = false; done(); }
    });
  }

  function pushPause(s, e) {
    if (sessionStartTs == null) return;
    const d = Math.max(0, (e - s) / 1000);
    if (d <= 0) return;
    currentAnswerPauses.push({ start: (s-sessionStartTs)/1000, end: (e-sessionStartTs)/1000, duration_sec: +d.toFixed(2) });
  }

  function trackAnswerPause(rms, now) {
    if (currentAnswerStartTs == null || state !== "running") return;
    if (rms > CONFIG.VAD_THRESHOLD) {
      if (currentPauseStartTs != null) { pushPause(currentPauseStartTs, now); currentPauseStartTs = null; }
      currentPauseCandidateTs = null; return;
    }
    if (currentPauseStartTs != null) return;
    if (currentPauseCandidateTs == null) { currentPauseCandidateTs = now; return; }
    if (now - currentPauseCandidateTs >= CONFIG.VAD_HANG_MS) currentPauseStartTs = currentPauseCandidateTs;
  }

  async function consumeCurrentAnswerSpeechMetrics(now) {
    if (currentPauseStartTs != null) pushPause(currentPauseStartTs, now);
    else if (currentPauseCandidateTs != null && now - currentPauseCandidateTs >= CONFIG.VAD_HANG_MS) pushPause(currentPauseCandidateTs, now);
    await stopAnswerSpeechCapture();
    const transcript = buildCurrentAnswerTranscript();
    const pauses = currentAnswerPauses.slice();
    const totalPauseSec = pauses.reduce((s,i) => s + +(i.duration_sec||0), 0);
    const maxPauseSec = pauses.reduce((m,i) => Math.max(m, +(i.duration_sec||0)), 0);
    resetAnswerSpeechMetrics();
    return { transcript, pauses, totalPauseSec: +totalPauseSec.toFixed(2), maxPauseSec: +maxPauseSec.toFixed(2) };
  }

  // --- Timer ---

  let remainingSec = 0, timer = null;

  function formatMMSS(t) { const s = Math.max(0,t); return `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`; }
  function updateTimer() { if (timerElement) timerElement.textContent = formatMMSS(remainingSec); }

  function startGlobalCountdown() {
    if (timer) clearInterval(timer);
    remainingSec = CONFIG.totalLimitSec || CONFIG.DEFAULT_TOTAL_LIMIT_SEC;
    updateTimer();
    timer = setInterval(() => {
      remainingSec--;
      updateTimer();
      if (remainingSec <= 0) { clearInterval(timer); timer = null; remainingSec = 0; updateTimer(); finishInterviewByTimeout(); }
    }, CONFIG.TIMER_TICK_MS);
  }
  function stopTimer() { if (timer) clearInterval(timer); timer = null; }

  // --- UI ---

  function setStatus(text) { if (statusEl) statusEl.textContent = text || ""; }

  function resetFeedback() {
    if (feedbackPanel) feedbackPanel.style.display = "none";
    if (feedbackScoreEl) feedbackScoreEl.textContent = "";
    if (feedbackVerdictEl) feedbackVerdictEl.textContent = "";
    if (feedbackCriteriaEl) feedbackCriteriaEl.innerHTML = "";
  }

  function renderFeedback(fb) {
    if (!fb || !feedbackPanel) return;
    feedbackPanel.style.display = "block";
    if (feedbackScoreEl) feedbackScoreEl.textContent = Number(fb.score||0).toFixed(2);
    if (feedbackVerdictEl) feedbackVerdictEl.textContent = fb.verdict || "";
    if (feedbackCriteriaEl) {
      feedbackCriteriaEl.innerHTML = "";
      const ul = document.createElement("ul"); ul.className = "mb-0";
      for (const [n,v] of Object.entries(fb.criteria_results || {})) {
        const li = document.createElement("li");
        li.textContent = `${n}: ${Number(v?.result||0).toFixed(2)}${v?.verdict ? ` — ${v.verdict}` : ""}`;
        ul.appendChild(li);
      }
      feedbackCriteriaEl.appendChild(ul);
    }
  }

  function setButtons({ mainText, mainEnabled, showNext }) {
    if (mainBtn) { mainBtn.textContent = mainText; mainBtn.disabled = !mainEnabled; }
    if (nextBtn) nextBtn.style.display = showNext ? "inline-block" : "none";
  }

  function showInterviewUI() {
    if (interviewInfo) interviewInfo.classList.remove("is-hidden");
  }
  function hideInterviewUI() {
    if (interviewInfo) interviewInfo.classList.add("is-hidden");
    if (avatarVideo) avatarVideo.style.display = "none";
  }

  function updateQuestionProgress() {
    if (questionNumberEl) questionNumberEl.textContent = String(questionIndex + 1);
    if (nextBtn) nextBtn.textContent = questionIndex === questions.length - 1 ? "Закончить" : "Следующий вопрос";
  }

  // --- Recording ---

  let sessionRecorder = null, fullSessionChunks = [];

  function pickMime() {
    for (const t of ["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg"])
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
    return null;
  }

  async function ensureMic() {
    if (mediaStream) return mediaStream;
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return mediaStream;
  }
  function stopMediaStream() {
    if (!mediaStream) return;
    try { mediaStream.getTracks().forEach(t => t.stop()); } catch {}
    mediaStream = null;
  }

  async function startSessionRecording() {
    await ensureMic();
    fullSessionChunks = [];
    sessionStartTs = performance.now();
    questionSegments = [];
    const mime = pickMime();
    sessionRecorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime }) : new MediaRecorder(mediaStream);
    sessionRecorder.ondataavailable = (e) => { if (e.data?.size > 0) fullSessionChunks.push(e.data); };
    sessionRecorder.start();
    startMicIndicator();
  }

  function stopSessionRecording({ upload = true } = {}) {
    if (!sessionRecorder) { stopMediaStream(); return Promise.resolve(); }
    const rec = sessionRecorder; sessionRecorder = null;
    return new Promise((resolve) => {
      rec.onstop = () => {
        if (upload && fullSessionChunks.length > 0) {
          const blob = new Blob(fullSessionChunks, { type: "audio/webm" });
          sendSessionToBackend(blob);
        }
        fullSessionChunks = [];
        stopMediaStream();
        resolve();
      };
      if (rec.state === "inactive") { rec.onstop(); return; }
      try { rec.stop(); } catch { fullSessionChunks = []; stopMediaStream(); resolve(); }
    });
  }

  let vadInterval = null;
  function startMicIndicator() {
    if (!mediaStream) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = new AC(), src = ctx.createMediaStreamSource(mediaStream), an = ctx.createAnalyser();
    an.fftSize = 1024; src.connect(an);
    const buf = new Uint8Array(an.fftSize);
    setMic(true);
    vadInterval = setInterval(() => {
      an.getByteTimeDomainData(buf);
      let sum = 0; for (let i = 0; i < buf.length; i++) { const x = (buf[i]-128)/128; sum += x*x; }
      const rms = Math.sqrt(sum/buf.length), now = performance.now();
      trackAnswerPause(rms, now);
      setMicSpeaking(rms > CONFIG.VAD_THRESHOLD);
    }, 50);
  }
  function stopMicIndicator() { if (vadInterval) clearInterval(vadInterval); vadInterval = null; setMicSpeaking(false); setMic(false); }

  // --- Flow ---

  async function closeCurrentAnswer() {
    if (currentAnswerStartTs == null) return;
    const now = performance.now(), q = getCurrentQuestion();
    const m = await consumeCurrentAnswerSpeechMetrics(now);
    const seg = {
      question_id: q?.id || null, order: questionIndex,
      start: (currentAnswerStartTs - sessionStartTs)/1000, end: (now - sessionStartTs)/1000,
      transcript: m.transcript, pauses: m.pauses,
      total_pause_sec: m.totalPauseSec, max_pause_sec: m.maxPauseSec,
    };
    questionSegments.push(seg);
    logResearchEvent("answer_transcript_received", { ...seg, question_text: q?.text || "", client_time_iso: new Date().toISOString() });
    currentAnswerStartTs = null;
  }

  function resetForRestart() {
    questionIndex = 0; recordedDurationSec = 0; sessionStartTs = null; currentAnswerStartTs = null;
    questionSegments = []; fullSessionChunks = [];
    resetAnswerSpeechMetrics(); stopAnswerSpeechCapture();
    if (questionNumberEl) questionNumberEl.textContent = "1";
    if (questionTotalEl) questionTotalEl.textContent = String(questions.length);
    resetFeedback();
  }

  async function loadInterviewData() {
    dataLoaded = false; questions = [];
    setButtons({ mainText: "Загрузка...", mainEnabled: false, showNext: false });
    setStatus("Загружаю данные интервью...");

    try {
      const resp = await fetch(API.SESSION_DATA_URL, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) { if (data?.redirect_url) { window.location.href = data.redirect_url; return; } throw new Error(data?.error || "Ошибка"); }

      questions = Array.isArray(data.questions) ? data.questions : [];
      const sec = normalizePositiveInt(data.session_timer_seconds, 0);
      const min = normalizePositiveInt(data.session_timer_minutes, 0);
      if (sec > 0) CONFIG.totalLimitSec = sec;
      else if (min > 0) CONFIG.totalLimitSec = min * 60;
      updateTimer();

      if (!questions.length) { if (data?.redirect_url) { window.location.href = data.redirect_url; return; } throw new Error("Вопросы не найдены"); }

      questionIndex = 0; dataLoaded = true;
      if (questionTotalEl) questionTotalEl.textContent = String(questions.length);

      setStatus("Нажмите «Начать» для старта интервью");
      setButtons({ mainText: "Начать", mainEnabled: true, showNext: false });
    } catch (err) {
      questions = [];
      setStatus(err?.message || "Ошибка загрузки");
      setButtons({ mainText: "Начать", mainEnabled: false, showNext: false });
    }
  }

  async function startInterview() {
    if (!dataLoaded || !questions.length) return;
    showInterviewUI();
    resetForRestart();
    state = "running";
    setStatus("Готовлю интервью...");
    setButtons({ mainText: "Запускаем...", mainEnabled: false, showNext: false });

    try { await startSessionRecording(); } catch {
      state = "idle"; stopTimer(); stopMicIndicator(); stopMediaStream();
      setStatus("Не удалось получить доступ к микрофону.");
      setButtons({ mainText: "Начать", mainEnabled: true, showNext: false });
      return;
    }

    startGlobalCountdown();
    updateQuestionProgress();
    await askQuestion();
  }

  async function askQuestion() {
    const q = getCurrentQuestion();
    if (!q) return;

    setStatus("Воспроизведение вопроса...");
    setButtons({ mainText: "Воспроизведение...", mainEnabled: false, showNext: false });

    logResearchEvent("question_shown", {
      question_id: q.id, order: questionIndex, total_questions: questions.length,
      text: q.text, client_time_iso: new Date().toISOString(),
    });

    await playQuestionVideo(questionIndex);

    // Предзагрузка следующего видео
    if (questionIndex + 1 < questions.length) {
      const nextQ = questions[questionIndex + 1];
      if (nextQ?.avatar_video_url) {
        const link = document.createElement("link");
        link.rel = "prefetch";
        link.as = "video";
        link.href = nextQ.avatar_video_url;
        document.head.appendChild(link);
      }
    }

    currentAnswerStartTs = performance.now();
    startAnswerSpeechCapture();
    setStatus("Говорите ответ");
    setButtons({ mainText: "Идёт запись", mainEnabled: false, showNext: true });
  }

  async function nextQuestion() {
    await closeCurrentAnswer();
    if (questionIndex < questions.length - 1) {
      questionIndex++;
      updateQuestionProgress();
      await askQuestion();
      return;
    }
    await finishInterview();
  }

  async function finishInterview() {
    await closeCurrentAnswer();
    recordedDurationSec = sessionStartTs == null ? 0 : (performance.now() - sessionStartTs) / 1000;
    state = "finished"; stopTimer(); stopMicIndicator();
    await stopSessionRecording({ upload: true });
    hideInterviewUI();
    setStatus("Интервью завершено");
    setButtons({ mainText: "Начать заново", mainEnabled: true, showNext: false });
  }

  function finishInterviewByTimeout() { setStatus("Время вышло"); finishInterview(); }

  function buildUploadSegments() {
    return questionSegments.map(s => ({ question_id: s.question_id, order: s.order, start: s.start, end: s.end }));
  }

  async function sendSessionToBackend(blob) {
    setStatus("Отправляю запись...");
    const form = new FormData();
    form.append("audio", blob, "interview_full.webm");
    form.append("segments", JSON.stringify(buildUploadSegments()));
    form.append("duration", String(recordedDurationSec.toFixed(2)));

    try {
      const resp = await fetch(API.RECORDING_URL, { method: "POST", headers: { Accept: "application/json" }, credentials: "same-origin", body: form });
      const data = await resp.json().catch(() => ({}));
      if (data.results_url) { window.location.href = data.results_url; return; }
      if (data.processing) { setStatus(data.message || "Интервью сохранено."); return; }
      if (data.feedback) { renderFeedback(data.feedback); setStatus("Интервью завершено"); return; }
      setStatus(data?.error || "Интервью завершено");
    } catch { setStatus("Ошибка при отправке"); }
  }

  // --- Events ---

  mainBtn?.addEventListener("click", async () => {
    if (state === "idle" || state === "finished") await startInterview();
  });
  nextBtn?.addEventListener("click", nextQuestion);

  // --- Init ---

  hideInterviewUI();
  setButtons({ mainText: "Загрузка...", mainEnabled: false, showNext: false });
  setStatus("Загружаю данные интервью...");
  loadInterviewData();
});
