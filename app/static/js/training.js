let pdfDoc,
    pageNum,
    pageRendering,
    pageNumPending,
    scale,
    canvas,
    ctx,
    trainingId,
    currentPage;

function waitForLogger(callback, timeout = 3000) {
    const start = Date.now();

    (function check() {
        if (typeof window.logger === 'object' && typeof window.logger.log === 'function') {
            callback();
            return;
        }

        if (Date.now() - start > timeout) {
            console.error('Logger not loaded');
            return;
        }

        setTimeout(check, 50);
    })();
}

function renderPage(num) {
  pageRendering = true;
  pdfDoc.getPage(num).then(function(page) {
    let viewport = page.getViewport({ scale: scale });
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    let renderContext = {
      canvasContext: ctx,
      viewport: viewport,
    };
    let renderTask = page.render(renderContext);

    renderTask.promise.then(function () {
      pageRendering = false;
      if (pageNumPending !== null) {
        renderPage(pageNumPending);
        pageNumPending = null;
      }
    });
  });
  $("#page_num")[0].textContent = num;
}

function queueRenderPage(num) {
  if (pageRendering) {
    pageNumPending = num;
  } else {
    renderPage(num);
  }
}

function callShowPage() {
  $.ajax({
    type: "PUT",
    url: `/api/trainings/timestamps/${trainingId}/?timestamp=${Date.now() / 1000}`
  });
}

function onNextPage() {
  if (pageNum >= pdfDoc.numPages) {
    return;
  }
  pageNum++;
  waitForLogger(() => logger.log('[TRAINING] slide_changed', `to=${pageNum}`));
  callShowPage();
  queueRenderPage(pageNum);
}

function setPage(pageNum){
  if (pageNum > pdfDoc.numPages) {
    return;
  }
  if (currentPage == pageNum){
    return;
  }
  currentPage = pageNum;
  waitForLogger(() => logger.log('[TRAINING] slide_set', `to=${pageNum}`));
  changeURLByParam('page', currentPage);
  queueRenderPage(pageNum);
}

function setupPresentationViewer(trainingId_) {
    trainingId = trainingId_;

    // logger.setTrainingId(trainingId_);
    waitForLogger(() => {
        logger.log('[TRAINING] presentation_viewer_initialized');
    });


    let loadingTask = pdfjsLib.getDocument(`/api/files/presentations/by-training/${trainingId_}/`);
    loadingTask.promise.then(function(pdfDoc_) {
      pdfDoc = pdfDoc_;
      $("#page_count")[0].textContent = pdfDoc.numPages;
      renderPage(pageNum);
    });
}

$(document).ready(function() {
    $("#alert").hide();
    pdfDoc = null;
    pageNum = 1;
    pageRendering = false;
    pageNumPending = null;
    scale = 1.1;
    canvas = $("#the-canvas")[0];
    ctx = canvas.getContext("2d");
    $("#done").click(function () {
        waitForLogger(() => logger.log('[TRAINING] done_clicked'));
        callShowPage();
    });
    $("#next").click(onNextPage);
});
