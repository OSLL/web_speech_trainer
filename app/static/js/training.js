let pdfDoc,
    pageNum,
    pageRendering,
    pageNumPending,
    scale,
    canvas,
    ctx,
    presentationFileId;

function renderPage(num) {
  pageRendering = true;
  // Using promise to fetch the page
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

  // Update page counters
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
      presentationFileId: presentationFileId
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

function setPresentationFileId(fileId) {
    presentationFileId = fileId;
    let loadingTask = pdfjsLib.getDocument(`/get_presentation_file?presentationFileId=${presentationFileId}`);
    loadingTask.promise.then(function(pdfDoc_) {
      pdfDoc = pdfDoc_;
      $('#page_count')[0].textContent = pdfDoc.numPages;
      renderPage(pageNum);
    });
}

$(document).ready(function() {
    pdfDoc = null;
    pageNum = 1;
    pageRendering = false;
    pageNumPending = null;
    scale = 0.9;
    canvas = $('#the-canvas')[0];
    ctx = canvas.getContext('2d');
    $('#done').click(callShowPage);
    $('#next').click(onNextPage);
});
