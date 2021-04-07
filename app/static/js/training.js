let pdfDoc,
    pageNum,
    pageRendering,
    pageNumPending,
    scale,
    canvas,
    ctx,
    presentationFileId,
    trainingId;

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
  $('#page_num')[0].textContent = num;
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
    type: 'GET',
    url: '/show_page',
    data: {
      trainingId: trainingId
    }
  });
}

function returnToUploadPage() {
  window.location.replace("/upload");
}

function onNextPage() {
  if (pageNum >= pdfDoc.numPages) {
    return;
  }
  pageNum++;
  callShowPage();
  queueRenderPage(pageNum);
}

function setupPresentationViewer(presentationFileId_, trainingId_) {
    presentationFileId = presentationFileId_;
    trainingId = trainingId_;
    let loadingTask = pdfjsLib.getDocument(`/get_presentation_file?presentationFileId=${presentationFileId}`);
    loadingTask.promise.then(function(pdfDoc_) {
      pdfDoc = pdfDoc_;
      $('#page_count')[0].textContent = pdfDoc.numPages;
      renderPage(pageNum);
    });
}

$(document).ready(function() {

    $('#alert').hide()

    navigator.mediaDevices.getUserMedia({ audio: true}).then(stream => {

    }).catch( err => {
        $('#alert').show()
        str = "Microphone is not available!"
        $('#error-text').html(str)
    })

    pdfDoc = null;
    pageNum = 1;
    pageRendering = false;
    pageNumPending = null;
    scale = 1.1;
    canvas = $('#the-canvas')[0];
    ctx = canvas.getContext('2d');
    $('#done').click(callShowPage);
    $('#next').click(onNextPage);
});
