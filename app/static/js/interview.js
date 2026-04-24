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

  const timerSection = document.querySelector(".timer-section");
  const timerElement = document.getElementById("timer");

  const mainBtn = document.getElementById("main-btn");
  const nextBtn = document.getElementById("next-btn");

  const questionNumberEl = document.getElementById("question-number");
  const questionTotalEl = document.getElementById("question-total");
  const questionTextEl = document.getElementById("question-text");
  const questionPlaceholderEl = document.getElementById("question-placeholder");

  const statusEl = document.getElementById("status");
  const micIndicator = document.getElementById("mic-indicator");
  const recordingsEl = document.getElementById("recordings");
  const pageRoot = document.querySelector(".interview-container");

  function normalizePositiveInt(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  const bootstrapSessionTimerMinutes = normalizePositiveInt(
    pageRoot?.dataset?.sessionTimerMinutes,
    0,
  );
  if (bootstrapSessionTimerMinutes > 0) {
    CONFIG.totalLimitSec = bootstrapSessionTimerMinutes * 60;
  }

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

  function getCurrentQuestion() {
    return questions[questionIndex] || null;
  }

  function logResearchEvent(event, meta = {}) {
    return fetch(API.RESEARCH_EVENT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ event, meta }),
    }).catch((err) => {
      console.warn("Research event log failed:", event, err);
    });
  }

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

  function getSpeechRecognitionCtor() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  function ensureSpeechRecognition() {
    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (!SpeechRecognitionCtor) return null;
    if (recognition) return recognition;

    recognition = new SpeechRecognitionCtor();
    recognition.lang = "ru-RU";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      if (currentAnswerStartTs == null) return;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcript = result[0]?.transcript?.trim();
        if (!transcript) continue;

        if (result.isFinal) {
          currentAnswerTranscriptFinalParts.push(transcript);
          currentAnswerTranscriptInterimByIndex.delete(i);
        } else {
          currentAnswerTranscriptInterimByIndex.set(i, transcript);
        }
      }
    };

    recognition.onerror = (event) => {
      console.warn("SpeechRecognition error:", event);
    };

    recognition.onend = () => {
      recognitionActive = false;

      if (recognitionStopResolver) {
        const resolve = recognitionStopResolver;
        recognitionStopResolver = null;
        resolve();
      }

      if (!recognitionShouldRun || state !== "running" || currentAnswerStartTs == null) return;
      try {
        recognition.start();
        recognitionActive = true;
      } catch (err) {
        console.warn("Не удалось перезапустить SpeechRecognition:", err);
      }
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
    const interimParts = Array.from(currentAnswerTranscriptInterimByIndex.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([, value]) => value);

    return [...currentAnswerTranscriptFinalParts, ...interimParts]
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function startAnswerSpeechCapture() {
    resetAnswerSpeechMetrics();
    currentPauseCandidateTs = performance.now();
    recognitionShouldRun = true;

    const speechRecognition = ensureSpeechRecognition();
    if (!speechRecognition || recognitionActive) return;

    try {
      speechRecognition.start();
      recognitionActive = true;
    } catch (err) {
      console.warn("Не удалось запустить SpeechRecognition:", err);
    }
  }

  function stopAnswerSpeechCapture() {
    recognitionShouldRun = false;

    if (!recognition || !recognitionActive) {
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      let timeoutId = null;

      const finishStop = () => {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        recognitionStopResolver = null;
        resolve();
      };

      recognitionStopResolver = finishStop;

      timeoutId = setTimeout(() => {
        recognitionActive = false;
        finishStop();
      }, 800);

      try {
        recognition.stop();
      } catch (err) {
        console.warn("Не удалось остановить SpeechRecognition:", err);
        recognitionActive = false;
        finishStop();
      }
    });
  }

  function pushPause(startTs, endTs) {
    if (sessionStartTs == null) return;
    const durationSec = Math.max(0, (endTs - startTs) / 1000);
    if (durationSec <= 0) return;

    currentAnswerPauses.push({
      start: (startTs - sessionStartTs) / 1000,
      end: (endTs - sessionStartTs) / 1000,
      duration_sec: Number(durationSec.toFixed(2)),
    });
  }

  function trackAnswerPause(rms, nowTs) {
    if (currentAnswerStartTs == null || state !== "running") return;

    const speaking = rms > CONFIG.VAD_THRESHOLD;

    if (speaking) {
      if (currentPauseStartTs != null) {
        pushPause(currentPauseStartTs, nowTs);
        currentPauseStartTs = null;
      }
      currentPauseCandidateTs = null;
      return;
    }

    if (currentPauseStartTs != null) return;

    if (currentPauseCandidateTs == null) {
      currentPauseCandidateTs = nowTs;
      return;
    }

    if (nowTs - currentPauseCandidateTs >= CONFIG.VAD_HANG_MS) {
      currentPauseStartTs = currentPauseCandidateTs;
    }
  }

  async function consumeCurrentAnswerSpeechMetrics(nowTs) {
    if (currentPauseStartTs != null) {
      pushPause(currentPauseStartTs, nowTs);
    } else if (
      currentPauseCandidateTs != null &&
      nowTs - currentPauseCandidateTs >= CONFIG.VAD_HANG_MS
    ) {
      pushPause(currentPauseCandidateTs, nowTs);
    }

    await stopAnswerSpeechCapture();

    const transcript = buildCurrentAnswerTranscript();
    const pauses = currentAnswerPauses.slice();
    const totalPauseSec = pauses.reduce((sum, item) => sum + Number(item?.duration_sec || 0), 0);
    const maxPauseSec = pauses.reduce(
      (max, item) => Math.max(max, Number(item?.duration_sec || 0)),
      0,
    );

    resetAnswerSpeechMetrics();

    return {
      transcript,
      pauses,
      totalPauseSec: Number(totalPauseSec.toFixed(2)),
      maxPauseSec: Number(maxPauseSec.toFixed(2)),
    };
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

    remainingSec = CONFIG.totalLimitSec || CONFIG.DEFAULT_TOTAL_LIMIT_SEC;
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
    if (timerSection) timerSection.classList.add("is-hidden");
  }

  function showInterviewUI() {
    if (timerSection) timerSection.classList.remove("is-hidden");
  }

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text || "";
  }

  function showQuestionPlaceholder(text) {
    if (questionPlaceholderEl) {
      questionPlaceholderEl.textContent = text || "Вопросы появятся здесь после старта интервью";
      questionPlaceholderEl.style.display = "block";
    }
  }

  function hideQuestionPlaceholder() {
    if (questionPlaceholderEl) questionPlaceholderEl.style.display = "none";
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
    const q = getCurrentQuestion();
    if (!q) return;

    hideQuestionPlaceholder();

    if (questionNumberEl) questionNumberEl.textContent = String(questionIndex + 1);
    if (questionTextEl) questionTextEl.textContent = q.text || "";

    if (nextBtn) {
      nextBtn.textContent =
        questionIndex === questions.length - 1 ? "Закончить" : "Следующий вопрос";
    }
    logResearchEvent("question_shown", {
      question_id: q?.id || q?._id || null,
      order: questionIndex,
      number: questionIndex + 1,
      total_questions: questions.length,
      text: q?.text || "",
      client_time_iso: new Date().toISOString(),
      session_elapsed_sec: sessionStartTs == null
        ? null
        : Number(((performance.now() - sessionStartTs) / 1000).toFixed(2)),
    });
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

  function stopMediaStream() {
    if (!mediaStream) return;
    try {
      mediaStream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      console.warn("Не удалось остановить медиапоток:", err);
    }
    mediaStream = null;
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

  function stopSessionRecording({ upload = true, renderRecording = true } = {}) {
    if (!sessionRecorder) {
      stopMediaStream();
      return Promise.resolve();
    }

    const recorder = sessionRecorder;
    sessionRecorder = null;

    return new Promise((resolve) => {
      recorder.onstop = () => {
        if (upload && fullSessionChunks.length > 0) {
          const blob = new Blob(fullSessionChunks, { type: "audio/webm" });
          if (renderRecording) addFullSessionRecording(blob);
          sendSessionToBackend(blob);
        }

        fullSessionChunks = [];
        stopMediaStream();
        resolve();
      };

      if (recorder.state === "inactive") {
        recorder.onstop();
        return;
      }

      try {
        recorder.stop();
      } catch (err) {
        console.warn("Не удалось остановить recorder:", err);
        fullSessionChunks = [];
        stopMediaStream();
        resolve();
      }
    });
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
      const nowTs = performance.now();
      trackAnswerPause(rms, nowTs);
      setMicSpeaking(rms > CONFIG.VAD_THRESHOLD);
    }, 50);
  }

  function stopMicIndicator() {
    if (vadInterval) clearInterval(vadInterval);
    vadInterval = null;
    setMicSpeaking(false);
    setMic(false);
  }

  async function closeCurrentAnswer() {
    if (currentAnswerStartTs == null) return;
    const now = performance.now();
    const q = getCurrentQuestion();
    const answerSpeechMetrics = await consumeCurrentAnswerSpeechMetrics(now);

    const answerSegment = {
      question_id: q?.id || q?._id || null,
      order: questionIndex,
      start: (currentAnswerStartTs - sessionStartTs) / 1000,
      end: (now - sessionStartTs) / 1000,
      transcript: answerSpeechMetrics.transcript,
      pauses: answerSpeechMetrics.pauses,
      total_pause_sec: answerSpeechMetrics.totalPauseSec,
      max_pause_sec: answerSpeechMetrics.maxPauseSec,
    };

    questionSegments.push(answerSegment);

    logResearchEvent("answer_transcript_received", {
      ...answerSegment,
      question_text: q?.text || "",
      client_time_iso: new Date().toISOString(),
      duration_sec: Number((answerSegment.end - answerSegment.start).toFixed(2)),
    });
    currentAnswerStartTs = null;
  }

  function resetInterviewStateForRestart() {
    questionIndex = 0;
    recordedDurationSec = 0;
    sessionStartTs = null;
    currentAnswerStartTs = null;
    questionSegments = [];
    fullSessionChunks = [];
    resetAnswerSpeechMetrics();
    stopAnswerSpeechCapture();

    if (recordingsEl) recordingsEl.innerHTML = "";
    if (questionTextEl) questionTextEl.textContent = "";
    if (questionNumberEl) questionNumberEl.textContent = "1";
    if (questionTotalEl) questionTotalEl.textContent = String(questions.length);

    showQuestionPlaceholder("Вопросы появятся здесь после старта интервью");
    resetFeedback();
  }

  async function loadInterviewData() {
    dataLoaded = false;
    questions = [];

    setButtons({ mainText: "Загрузка...", mainEnabled: false, showNext: false });
    showQuestionPlaceholder("Загружаем вопросы интервью...");
    setStatus("Загружаю данные интервью...");

    try {
      const resp = await fetch(API.SESSION_DATA_URL, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        if (data?.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }
        throw new Error(data?.error || "Не удалось загрузить данные интервью");
      }

      questions = Array.isArray(data.questions) ? data.questions : [];

      const apiSessionTimerSeconds = normalizePositiveInt(data.session_timer_seconds, 0);
      const apiSessionTimerMinutes = normalizePositiveInt(data.session_timer_minutes, 0);
      if (apiSessionTimerSeconds > 0) {
        CONFIG.totalLimitSec = apiSessionTimerSeconds;
      } else if (apiSessionTimerMinutes > 0) {
        CONFIG.totalLimitSec = apiSessionTimerMinutes * 60;
      }
      updateTimer();

      if (!questions.length) {
        if (data?.redirect_url) {
          window.location.href = data.redirect_url;
          return;
        }
        throw new Error("Вопросы для интервью не найдены");
      }

      questionIndex = 0;
      dataLoaded = true;

      if (questionTotalEl) {
        questionTotalEl.textContent = String(data.total_questions || questions.length);
      }

      showQuestionPlaceholder("Вопросы появятся здесь после старта интервью");
      setStatus("Нажмите «Начать», чтобы начать интервью");
      setButtons({ mainText: "Начать", mainEnabled: true, showNext: false });
    } catch (err) {
      questions = [];
      if (questionTotalEl) questionTotalEl.textContent = "0";
      showQuestionPlaceholder("Не удалось загрузить вопросы интервью");
      setStatus(err?.message || "Не удалось загрузить данные интервью");
      setButtons({ mainText: "Начать", mainEnabled: false, showNext: false });
    }
  }

  async function startInterview() {
    if (!dataLoaded || !questions.length) {
      setStatus("Вопросы еще не загружены");
      return;
    }

    showInterviewUI();
    resetInterviewStateForRestart();
    state = "running";

    renderQuestion();
    setStatus("Интервью началось");

    setButtons({ mainText: "Озвучить вопрос", mainEnabled: true, showNext: false });

    await startSessionRecording();
    startGlobalCountdown();
  }

  async function askQuestion() {
    const q = getCurrentQuestion();
    if (!q) return;

    setStatus("Озвучиваю вопрос…");
    setButtons({ mainText: "Озвучивается…", mainEnabled: false, showNext: false });

    await speak(q.text);

    currentAnswerStartTs = performance.now();
    startAnswerSpeechCapture();

    setStatus("Говорите ответ");
    setButtons({ mainText: "Озвучить вопрос", mainEnabled: false, showNext: true });
  }

  async function nextQuestion() {
    await closeCurrentAnswer();
    if (questionIndex < questions.length - 1) {
      questionIndex++;
      renderQuestion();
      await askQuestion();
      return;
    }
    await finishInterview();
  }

  async function finishInterview() {
    await closeCurrentAnswer();

    recordedDurationSec = sessionStartTs == null
      ? 0
      : (performance.now() - sessionStartTs) / 1000;

    state = "finished";
    stopTimer();
    stopMicIndicator();

    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    await stopSessionRecording({ upload: true, renderRecording: true });

    hideInterviewUI();
    setStatus("Интервью завершено");

    setButtons({ mainText: "Начать заново", mainEnabled: true, showNext: false });
  }

  function finishInterviewByTimeout() {
    setStatus("Время интервью вышло");
    finishInterview();
  }

  function addFullSessionRecording(blob) {
    if (!recordingsEl) return;

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
    const form = new FormData();
    form.append("audio", blob, "interview_full.webm");
    form.append("segments", JSON.stringify(questionSegments));
    form.append("duration", String(recordedDurationSec.toFixed(2)));

    try {
      const resp = await fetch(API.RECORDING_URL, {
        method: "POST",
        body: form,
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        console.warn("Ошибка отправки записи:", resp.status, data);
        setStatus(data?.error || "Не удалось сохранить интервью");
        return;
      }

      if (data.results_url) {
        window.location.href = data.results_url;
        return;
      }

      if (data.feedback) {
        renderFeedback(data.feedback);
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

  hideInterviewUI();
  showQuestionPlaceholder("Загружаем вопросы интервью...");
  setButtons({ mainText: "Загрузка...", mainEnabled: false, showNext: false });
  setStatus("Загружаю данные интервью...");

  loadInterviewData();
});