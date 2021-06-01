let pdfDoc,
    pageNum,
    pageRendering,
    pageNumPending,
    scale,
    canvas,
    ctx,
    trainingId;

function setupPresentationViewer(trainingId_) {
    let loadingTask = pdfjsLib.getDocument(`/api/files/presentations/by-training/${trainingId_}/`);
    loadingTask.promise.then(function(pdfDoc_) {
      pdfDoc = pdfDoc_;
      $("#page_count")[0].textContent = pdfDoc.numPages;
      renderPage(pageNum);
    });
}

$(document).ready(function() {
    pdfDoc = null;
    pageNum = 1;
    pageRendering = false;
    pageNumPending = null;
    scale = 1.1;
    canvas = $("#the-canvas")[0];
    ctx = canvas.getContext("2d");
});