(function () {
  function normalizeResultsPayload(rawPayload) {
    const payload = rawPayload?.data || rawPayload?.result || rawPayload || {};

    return {
      totalScore: Number(payload.total_score ?? payload.totalScore ?? 0),
      maxScore: Number(payload.max_score ?? payload.maxScore ?? 0),
      verdict: payload.verdict || "",
      questions: payload.questions || [],
      results: payload.results || payload.criteria || [],
      questionTotals: payload.question_totals || payload.questionTotals || []
    };
  }

  function init() {
    const pageRoot = document.getElementById("results-page");
    const totalScoreEl = document.getElementById("total-score");
    const resultsVerdictEl = document.getElementById("results-verdict");
    const questionsLegendEl = document.getElementById("questions-legend");
    const resultsHead = document.getElementById("results-head");
    const resultsBody = document.getElementById("results-body");
    const resultsFoot = document.getElementById("results-foot");
    const resultsUrl = pageRoot?.dataset?.resultsUrl;

    let DATA = {
      totalScore: 0,
      maxScore: 0,
      verdict: "",
      questions: [],
      results: [],
      questionTotals: []
    };

    function setLoadingState() {
      if (totalScoreEl) totalScoreEl.textContent = "Загрузка...";
      if (resultsVerdictEl) resultsVerdictEl.textContent = "";
      if (questionsLegendEl) questionsLegendEl.innerHTML = "";
      if (resultsHead) resultsHead.innerHTML = "";
      if (resultsBody) resultsBody.innerHTML = "";
      if (resultsFoot) resultsFoot.innerHTML = "";
    }

    function setErrorState(message) {
      const text = message || "Не удалось загрузить результаты интервью.";

      if (totalScoreEl) totalScoreEl.textContent = "—";
      if (resultsVerdictEl) resultsVerdictEl.textContent = text;
      if (questionsLegendEl) questionsLegendEl.innerHTML = "";
      if (resultsHead) resultsHead.innerHTML = "";
      if (resultsFoot) resultsFoot.innerHTML = "";

      if (!resultsBody) return;

      resultsBody.innerHTML = "";

      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 100;
      td.className = "criterion-name-cell";
      td.textContent = text;
      tr.appendChild(td);
      resultsBody.appendChild(tr);
    }

    function renderTotalScore() {
      if (!totalScoreEl) return;

      totalScoreEl.textContent = `${Number(DATA.totalScore || 0).toFixed(2)} / ${Number(DATA.maxScore || 0).toFixed(2)}`;

      const percent = DATA.maxScore
        ? Math.round((DATA.totalScore / DATA.maxScore) * 100)
        : 0;

      totalScoreEl.classList.remove("score-high", "score-medium", "score-low");

      if (percent >= 80) {
        totalScoreEl.classList.add("score-high");
      } else if (percent >= 50) {
        totalScoreEl.classList.add("score-medium");
      } else {
        totalScoreEl.classList.add("score-low");
      }

      if (resultsVerdictEl) {
        resultsVerdictEl.textContent = DATA.verdict || "";
      }
    }

    function renderQuestionsLegend() {
      if (!questionsLegendEl) return;

      questionsLegendEl.innerHTML = "";

      const title = document.createElement("div");
      title.className = "questions-legend-title";
      title.textContent = "Вопросы";
      questionsLegendEl.appendChild(title);

      const list = document.createElement("div");
      list.className = "questions-legend-list";

      (DATA.questions || []).forEach((question, index) => {
        const item = document.createElement("div");
        item.className = "questions-legend-item";

        const badge = document.createElement("span");
        badge.className = "question-badge";
        badge.textContent = `В${index + 1}`;

        const text = document.createElement("span");
        text.className = "question-legend-text";
        text.textContent = question.text || "";

        item.appendChild(badge);
        item.appendChild(text);
        list.appendChild(item);
      });

      questionsLegendEl.appendChild(list);
    }

    function renderHeader() {
      if (!resultsHead) return;

      resultsHead.innerHTML = "";

      const tr = document.createElement("tr");

      const firstTh = document.createElement("th");
      firstTh.textContent = "Критерий";
      tr.appendChild(firstTh);

      (DATA.questions || []).forEach((_, index) => {
        const th = document.createElement("th");
        th.className = "short-question-header";
        th.textContent = `В${index + 1}`;
        tr.appendChild(th);
      });

      const totalTh = document.createElement("th");
      totalTh.textContent = "Сумма";
      tr.appendChild(totalTh);

      resultsHead.appendChild(tr);
    }

    function createCell(score, comment) {
      const td = document.createElement("td");
      td.className = "result-cell";

      const scoreDiv = document.createElement("div");
      scoreDiv.className = "cell-score";
      scoreDiv.textContent = Number(score || 0).toFixed(2);

      const commentDiv = document.createElement("div");
      commentDiv.className = "cell-comment";
      commentDiv.textContent = comment || "—";

      td.appendChild(scoreDiv);
      td.appendChild(commentDiv);

      return td;
    }

    function renderBody() {
      if (!resultsBody) return;

      resultsBody.innerHTML = "";

      (DATA.results || []).forEach((row) => {
        const tr = document.createElement("tr");

        const nameTd = document.createElement("td");
        nameTd.className = "criterion-name-cell";
        nameTd.textContent = row.name || "—";
        tr.appendChild(nameTd);

        (row.cells || []).forEach((cell) => {
          tr.appendChild(createCell(cell.result, cell.verdict));
        });

        const totalTd = document.createElement("td");
        totalTd.className = "row-total-cell";
        totalTd.textContent = Number(row.total || 0).toFixed(2);
        tr.appendChild(totalTd);

        resultsBody.appendChild(tr);
      });
    }

    function renderFooter() {
      if (!resultsFoot) return;

      resultsFoot.innerHTML = "";

      const tr = document.createElement("tr");

      const titleTd = document.createElement("td");
      titleTd.className = "footer-title-cell";
      titleTd.textContent = "Итого по вопросам";
      tr.appendChild(titleTd);

      (DATA.questionTotals || []).forEach((value) => {
        const td = document.createElement("td");
        td.className = "footer-total-cell";
        td.textContent = Number(value || 0).toFixed(2);
        tr.appendChild(td);
      });

      const grandTd = document.createElement("td");
      grandTd.className = "footer-grand-total-cell";
      grandTd.textContent = Number(DATA.totalScore || 0).toFixed(2);
      tr.appendChild(grandTd);

      resultsFoot.appendChild(tr);
    }

    async function loadResults() {
      if (!resultsUrl) {
        setErrorState("Не задан URL для загрузки результатов интервью.");
        return;
      }

      setLoadingState();

      try {
        const response = await fetch(resultsUrl, {
          method: "GET",
          headers: {
            Accept: "application/json"
          },
          credentials: "same-origin"
        });

        const rawPayload = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(rawPayload?.message || rawPayload?.error || "Не удалось загрузить результаты интервью.");
        }

        DATA = normalizeResultsPayload(rawPayload);

        renderTotalScore();
        renderQuestionsLegend();
        renderHeader();
        renderBody();
        renderFooter();
      } catch (error) {
        setErrorState(error?.message);
      }
    }

    loadResults();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();