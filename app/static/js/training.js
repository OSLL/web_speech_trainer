var pdfDoc = null,
    pageNum = 1,
    pageRendering = false,
    pageNumPending = null,
    scale = 1.1,
    canvas = document.getElementById('the-canvas'),
    ctx = canvas.getContext('2d'),
    presentationFileId = null;

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
  document.getElementById('page_num').textContent = num;
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
document.getElementById('done').addEventListener('click', callShowPage);

function returnToUploadPage() {
  window.location.replace("/upload");
}
document.getElementById('done').addEventListener('click', returnToUploadPage);

function onNextPage() {
  if (pageNum >= pdfDoc.numPages) {
    return;
  }
  pageNum++;
  callShowPage();
  queueRenderPage(pageNum);
}
document.getElementById('next').addEventListener('click', onNextPage);


function setPresentationFileId(fileId) {
    presentationFileId = fileId;
    var loadingTask = pdfjsLib.getDocument(`/get_presentation_file?presentationFileId=${presentationFileId}`);
    loadingTask.promise.then(function(pdfDoc_) {
      pdfDoc = pdfDoc_;
      document.getElementById('page_count').textContent = pdfDoc.numPages;
      renderPage(pageNum);
    });
}
