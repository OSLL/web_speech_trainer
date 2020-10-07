var pdfDoc,
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
    var viewport = page.getViewport({ scale: scale, });
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    var renderContext = {
      canvasContext: ctx,
      viewport: viewport,
    };
    var renderTask = page.render(renderContext);

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
    var loadingTask = pdfjsLib.getDocument(`/get_presentation_file?presentationFileId=${presentationFileId}`);
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
    scale = 1.1;
    canvas = $('#the-canvas')[0];
    ctx = canvas.getContext('2d');
    presentationFileId = null;
    $('#done').click(callShowPage);
    $('#done').click(returnToUploadPage);
    $('#next').click(onNextPage);
});
