(() => {
  "use strict";

  const BOOTSTRAP_URL = "/api/interview/bootstrap/";
  const DEFAULT_SAVE_RECORDING_URL = "/api/interview/recording";

  const dom = {
    timerSection: document.querySelector(".timer-section"),
    timer: document.getElementById("timer"),
    questionNumber: document.getElementById("question-number"),
    questionTotal: document.getElementById("question-total"),
    questionPlaceholder: document.getElementById("question-placeholder"),
    questionText: document.getElementById("question-text"),
    status: document.getElementById("status"),
    feedbackPanel: document.getElementById("feedback-panel"),
    feedbackScore: document.getElementById("feedback-score"),
    feedbackVerdict: document.getElementById("feedback-verdict"),
    feedbackCriteria: document.getElementById("feedback-criteria"),
    mainBtn: document.getElementById("main-btn"),
    endAnswerBtn: document.getElementById("end-answer-btn"),
    nextBtn: document.getElementById("next-btn"),
    stopBtn: document.getElementById("stop-btn"),
    micIndicator: document.getElementById("mic-indicator"),
    recordings: document.getElementById("recordings"),
  };

  const state = {
    bootstrapLoaded: false,
    sessionId: null,
    cancelUrl: null,
    saveRecordingUrl: DEFAULT_SAVE_RECORDING_URL,
    questions: [],
    currentQuestionIndex: 0,
    interviewStarted: false,
    interviewFinished: false,
    currentQuestionStartedAt: null,
    currentQuestionText: "",
    currentAnswerStartAtSec: null,
    currentAnswerEndAtSec: null,
    segments: [],
    mediaRecorder: null,
    mediaStream: null,
    audioChunks: [],
    recordingStartedAtMs: null,
    recordingStopped: false,
    speechSupported: "speechSynthesis" in window,
    audioContext: null,
    analyser: null,
    micAnimationFrame: null,
  };

  function setStatus(text) {
    if (dom.status) {
      dom.status.textContent = text || "";
    }
  }

  function setQuestionText(text) {
    if (dom.questionPlaceholder) {
      dom.questionPlaceholder.style.display = text ? "none" : "";
    }
    if (dom.questionText) {
      dom.questionText.textContent = text || "";
    }
  }

  function updateQuestionCounter() {
    if (dom.questionNumber) {
      dom.questionNumber.textContent = String(state.currentQuestionIndex + 1);
    }
    if (dom.questionTotal) {
      dom.questionTotal.textContent = String(state.questions.length);
    }
  }

  function setMicActive(active) {
    if (!dom.micIndicator) return;
    dom.micIndicator.style.opacity = active ? "1" : "0.35";
  }

  function showTimerSection() {
    if (dom.timerSection) {
      dom.timerSection.classList.remove("is-hidden");
    }
  }

  function hideFeedback() {
    if (dom.feedbackPanel) {
      dom.feedbackPanel.style.display = "none";
    }
  }

  function showFeedback(feedback) {
    if (!dom.feedbackPanel) return;

    dom.feedbackPanel.style.display = "block";
    dom.feedbackScore.textContent = feedback?.score ?? "—";
    dom.feedbackVerdict.textContent = feedback?.verdict || "";

    const criteria = feedback?.criteria_results || {};
    const lines = Object.entries(criteria).map(([name, item]) => {
      const result = item?.result ?? "—";
      const verdict = item?.verdict ? ` — ${item.verdict}` : "";
      return `${name}: ${result}${verdict}`;
    });

    dom.feedbackCriteria.innerHTML = lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatSeconds(seconds) {
    const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
    const mm = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
    const ss = String(safeSeconds % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  function getElapsedRecordingSeconds() {
    if (!state.recordingStartedAtMs) return 0;
    return (Date.now() - state.recordingStartedAtMs) / 1000;
  }

  function getCurrentQuestionElapsedSeconds() {
    if (!state.currentQuestionStartedAt) return 0;
    return (Date.now() - state.currentQuestionStartedAt) / 1000;
  }

  let timerIntervalId = null;

  function startTimer() {
    stopTimer();
    timerIntervalId = window.setInterval(() => {
      if (dom.timer) {
        dom.timer.textContent = formatSeconds(getCurrentQuestionElapsedSeconds());
      }
    }, 200);
  }

  function stopTimer() {
    if (timerIntervalId) {
      window.clearInterval(timerIntervalId);
      timerIntervalId = null;
    }
  }

  function resetTimer() {
    stopTimer();
    if (dom.timer) {
      dom.timer.textContent = "00:00";
    }
  }

  function setButtonsForIdle() {
    dom.mainBtn.style.display = "";
    dom.mainBtn.disabled = !state.bootstrapLoaded || state.questions.length === 0;
    dom.mainBtn.textContent = state.interviewStarted ? "Повторить вопрос" : "Начать";

    dom.endAnswerBtn.style.display = "none";
    dom.nextBtn.style.display = "none";
  }

  function setButtonsForSpeaking() {
    dom.mainBtn.style.display = "";
    dom.mainBtn.disabled = true;
    dom.mainBtn.textContent = "Озвучивается…";

    dom.endAnswerBtn.style.display = "none";
    dom.nextBtn.style.display = "none";
  }

  function setButtonsForAnswering() {
    dom.mainBtn.style.display = "";
    dom.mainBtn.disabled = true;
    dom.mainBtn.textContent = "Идет ответ";

    dom.endAnswerBtn.style.display = "";
    dom.nextBtn.style.display = "none";
  }

  function setButtonsForAfterAnswer() {
    dom.mainBtn.style.display = "";
    dom.mainBtn.disabled = false;
    dom.mainBtn.textContent = "Повторить вопрос";

    dom.endAnswerBtn.style.display = "none";
    dom.nextBtn.style.display = "";
  }

  function setButtonsForFinished() {
    dom.mainBtn.style.display = "none";
    dom.endAnswerBtn.style.display = "none";
    dom.nextBtn.style.display = "none";
  }

  async function loadBootstrap() {
    const response = await fetch(BOOTSTRAP_URL, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.status === "failure" || payload.error) {
      const errorMessage = payload.error || "Не удалось загрузить данные интервью.";
      if (payload.redirect_url) {
        window.location.href = payload.redirect_url;
        return;
      }
      throw new Error(errorMessage);
    }

    state.sessionId = payload.sessionId || null;
    state.cancelUrl = payload.cancelUrl || null;
    state.saveRecordingUrl = payload.saveRecordingUrl || DEFAULT_SAVE_RECORDING_URL;
    state.questions = Array.isArray(payload.questions) ? payload.questions : [];
    state.bootstrapLoaded = true;

    updateQuestionCounter();
    setButtonsForIdle();
  }

  async function ensureMedia() {
    if (state.mediaRecorder && state.mediaStream) {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaStream = stream;
    state.audioChunks = [];

    const mimeTypeCandidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
    ];
    const selectedMimeType = mimeTypeCandidates.find((type) => window.MediaRecorder?.isTypeSupported?.(type));

    state.mediaRecorder = selectedMimeType
      ? new MediaRecorder(stream, { mimeType: selectedMimeType })
      : new MediaRecorder(stream);

    state.mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
      }
    });

    setupMicVisualizer(stream);
  }

  function setupMicVisualizer(stream) {
    try {
      state.audioContext = state.audioContext || new (window.AudioContext || window.webkitAudioContext)();
      const source = state.audioContext.createMediaStreamSource(stream);
      state.analyser = state.audioContext.createAnalyser();
      state.analyser.fftSize = 256;
      source.connect(state.analyser);

      const dataArray = new Uint8Array(state.analyser.frequencyBinCount);

      const tick = () => {
        if (!state.analyser) return;
        state.analyser.getByteTimeDomainData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i += 1) {
          const normalized = (dataArray[i] - 128) / 128;
          sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        setMicActive(rms > 0.03);

        state.micAnimationFrame = window.requestAnimationFrame(tick);
      };

      if (state.micAnimationFrame) {
        window.cancelAnimationFrame(state.micAnimationFrame);
      }
      state.micAnimationFrame = window.requestAnimationFrame(tick);
    } catch (error) {
      console.warn("Mic visualizer setup failed:", error);
    }
  }

  async function startRecordingIfNeeded() {
    await ensureMedia();

    if (!state.mediaRecorder) {
      throw new Error("MediaRecorder is not available");
    }

    if (state.mediaRecorder.state === "inactive") {
      state.audioChunks = [];
      state.recordingStartedAtMs = Date.now();
      state.recordingStopped = false;
      state.mediaRecorder.start();
    }
  }

  function stopRecordingAndGetBlob() {
    return new Promise((resolve, reject) => {
      if (!state.mediaRecorder) {
        reject(new Error("Recorder is not initialized"));
        return;
      }

      if (state.mediaRecorder.state === "inactive") {
        const fallbackBlob = new Blob(state.audioChunks, { type: state.mediaRecorder.mimeType || "audio/webm" });
        resolve(fallbackBlob);
        return;
      }

      const handleStop = () => {
        state.mediaRecorder.removeEventListener("stop", handleStop);
        const blob = new Blob(state.audioChunks, { type: state.mediaRecorder.mimeType || "audio/webm" });
        resolve(blob);
      };

      state.mediaRecorder.addEventListener("stop", handleStop, { once: true });

      try {
        state.mediaRecorder.stop();
        state.recordingStopped = true;
      } catch (error) {
        reject(error);
      }
    });
  }

  async function speak(text, timeoutMs = 8000) {
    if (!text) {
      return { ok: true, skipped: true };
    }

    if (!window.speechSynthesis) {
      return { ok: false, reason: "speechSynthesis_not_supported" };
    }

    return new Promise((resolve) => {
      let finished = false;
      let timeoutId = null;

      const finish = (result) => {
        if (finished) return;
        finished = true;
        if (timeoutId) {
          window.clearTimeout(timeoutId);
        }
        resolve(result);
      };

      try {
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "ru-RU";
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 1;

        utterance.onend = () => finish({ ok: true });
        utterance.onerror = (event) => finish({ ok: false, reason: event?.error || "speech_error" });

        timeoutId = window.setTimeout(() => {
          try {
            window.speechSynthesis.cancel();
          } catch (error) {
            console.warn("speechSynthesis.cancel failed:", error);
          }
          finish({ ok: false, reason: "timeout" });
        }, timeoutMs);

        window.speechSynthesis.resume?.();
        window.speechSynthesis.speak(utterance);
      } catch (error) {
        finish({ ok: false, reason: error?.message || "exception" });
      }
    });
  }

  async function askCurrentQuestion() {
    const question = state.questions[state.currentQuestionIndex];
    if (!question) {
      return;
    }

    state.currentQuestionText = question.text || "";
    updateQuestionCounter();
    setQuestionText(state.currentQuestionText);
    showTimerSection();
    hideFeedback();

    setButtonsForSpeaking();
    setStatus("Озвучиваю вопрос…");

    const speechResult = await speak(state.currentQuestionText);

    if (!speechResult.ok) {
      console.warn("Question TTS failed:", speechResult);
      setStatus("Автоозвучка недоступна. Прочитайте вопрос на экране и отвечайте голосом.");
    } else {
      setStatus("Говорите ответ");
    }

    state.currentQuestionStartedAt = Date.now();
    state.currentAnswerStartAtSec = getElapsedRecordingSeconds();
    state.currentAnswerEndAtSec = null;

    resetTimer();
    startTimer();
    setButtonsForAnswering();
  }

  async function startInterview() {
    if (!state.bootstrapLoaded) {
      setStatus("Данные интервью еще не загружены.");
      return;
    }

    if (state.questions.length === 0) {
      setStatus("Вопросы для интервью не найдены.");
      return;
    }

    state.interviewStarted = true;
    state.interviewFinished = false;
    state.currentQuestionIndex = 0;
    state.segments = [];
    state.currentQuestionStartedAt = null;
    state.currentAnswerStartAtSec = null;
    state.currentAnswerEndAtSec = null;
    state.recordingStartedAtMs = null;

    setQuestionText("");
    updateQuestionCounter();
    hideFeedback();

    await startRecordingIfNeeded();
    await askCurrentQuestion();
  }

  function finishCurrentAnswer() {
    if (!state.interviewStarted || state.interviewFinished) {
      return;
    }

    const question = state.questions[state.currentQuestionIndex];
    if (!question || state.currentAnswerStartAtSec == null) {
      return;
    }

    state.currentAnswerEndAtSec = getElapsedRecordingSeconds();
    stopTimer();

    state.segments.push({
      question_id: question.id,
      order: state.currentQuestionIndex,
      start: Number(state.currentAnswerStartAtSec.toFixed(3)),
      end: Number(state.currentAnswerEndAtSec.toFixed(3)),
      text: question.text,
    });

    appendRecordingRow({
      title: `Вопрос ${state.currentQuestionIndex + 1}`,
      duration: Math.max(0, state.currentAnswerEndAtSec - state.currentAnswerStartAtSec),
      text: question.text,
    });

    setStatus("Ответ завершен.");
    setButtonsForAfterAnswer();
  }

  async function goToNextQuestion() {
    if (state.currentQuestionIndex >= state.questions.length - 1) {
      await finishInterview();
      return;
    }

    state.currentQuestionIndex += 1;
    await askCurrentQuestion();
  }

  async function finishInterview() {
    if (state.interviewFinished) {
      return;
    }

    state.interviewFinished = true;
    stopTimer();
    setButtonsForFinished();
    setStatus("Сохраняем результаты интервью…");

    try {
      const audioBlob = await stopRecordingAndGetBlob();
      const responsePayload = await uploadInterviewRecording(audioBlob);

      showFeedback(responsePayload.feedback);
      setStatus("Интервью завершено.");

      if (responsePayload.results_url) {
        window.location.href = responsePayload.results_url;
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Не удалось сохранить результаты интервью.");
      setButtonsForAfterAnswer();
      state.interviewFinished = false;
    }
  }

  async function uploadInterviewRecording(audioBlob) {
    const formData = new FormData();
    formData.append("audio", audioBlob, "interview.webm");
    formData.append("segments", JSON.stringify(state.segments));
    formData.append("duration", String(getElapsedRecordingSeconds()));

    const response = await fetch(state.saveRecordingUrl || DEFAULT_SAVE_RECORDING_URL, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.error) {
      throw new Error(payload.error || "Не удалось сохранить запись интервью.");
    }

    return payload;
  }

  function appendRecordingRow({ title, duration, text }) {
    if (!dom.recordings) return;

    const item = document.createElement("div");
    item.className = "recordings-item";

    const safeTitle = escapeHtml(title);
    const safeText = escapeHtml(text || "");
    const durationText = formatSeconds(duration);

    item.innerHTML = `
      <div class="recordings-item-title">${safeTitle}</div>
      <div class="recordings-item-duration">${durationText}</div>
      <div class="recordings-item-text">${safeText}</div>
    `;

    dom.recordings.appendChild(item);
  }

  async function cancelSession() {
    if (!state.cancelUrl) {
      window.location.href = "/interview/upload/";
      return;
    }

    const confirmed = window.confirm("Прервать текущую сессию и вернуться к загрузке документа?");
    if (!confirmed) return;

    try {
      const response = await fetch(state.cancelUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
        },
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok || payload.error) {
        throw new Error(payload.error || "Не удалось прервать сессию.");
      }

      if (payload.redirect_url) {
        window.location.href = payload.redirect_url;
        return;
      }

      window.location.href = "/interview/upload/";
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Не удалось прервать сессию.");
    }
  }

  function bindEvents() {
    dom.mainBtn?.addEventListener("click", async () => {
      try {
        if (!state.interviewStarted) {
          await startInterview();
        } else if (!state.interviewFinished) {
          await askCurrentQuestion();
        }
      } catch (error) {
        console.error(error);
        setStatus(error.message || "Не удалось запустить интервью.");
      }
    });

    dom.endAnswerBtn?.addEventListener("click", () => {
      finishCurrentAnswer();
    });

    dom.nextBtn?.addEventListener("click", async () => {
      try {
        await goToNextQuestion();
      } catch (error) {
        console.error(error);
        setStatus(error.message || "Не удалось перейти к следующему вопросу.");
      }
    });

    dom.stopBtn?.addEventListener("click", async () => {
      await cancelSession();
    });

    window.addEventListener("beforeunload", () => {
      stopTimer();
      if (state.micAnimationFrame) {
        window.cancelAnimationFrame(state.micAnimationFrame);
      }
      if (state.mediaStream) {
        state.mediaStream.getTracks().forEach((track) => track.stop());
      }
      try {
        window.speechSynthesis?.cancel?.();
      } catch (error) {
        console.warn("speechSynthesis cancel failed:", error);
      }
    });
  }

  async function init() {
    setButtonsForIdle();
    hideFeedback();
    resetTimer();
    setStatus("Загружаем данные интервью…");

    bindEvents();

    try {
      await loadBootstrap();

      if (state.questions.length === 0) {
        setStatus("Вопросы для интервью не найдены.");
        dom.mainBtn.disabled = true;
        return;
      }

      setStatus("");
      updateQuestionCounter();
      setButtonsForIdle();
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Не удалось загрузить интервью.");
      dom.mainBtn.disabled = true;
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();