(function () {
  function init() {
    var pageRoot = document.getElementById('interview-upload-page');
    if (!pageRoot) {
      return;
    }

    var config = {
      uploadStateUrl: pageRoot.dataset.uploadStateUrl || '/api/interview/upload-page-state/',
      statusUrl: pageRoot.dataset.statusUrl || '/api/interview/questions-generation-status/',
      interviewUrl: pageRoot.dataset.interviewUrl || '/interview/',
      uploadUrl: pageRoot.dataset.uploadUrl || '/interview/upload/',
      defaultPollIntervalMs: Number(pageRoot.dataset.defaultPollIntervalMs || 2000)
    };

    var bootstrapMode = document.getElementById('upload-page-bootstrap-mode');
    var uploadMode = document.getElementById('upload-mode');
    var processingMode = document.getElementById('processing-mode');
    var uploadError = document.getElementById('upload-error');
    var processingStatusText = document.getElementById('processing-status-text');
    var currentDocument = document.getElementById('current-document');
    var processingCurrentDocument = document.getElementById('processing-current-document');
    var fileInput = document.getElementById('document');
    var selectedFileName = document.getElementById('selected-file-name');
    var uploadForm = document.getElementById('upload-form');
    var uploadSubmitBtn = document.getElementById('upload-submit-btn');

    var pollTimer = null;
    var pollIntervalMs = config.defaultPollIntervalMs;
    var currentProcessingDocumentName = '';

    function showElement(element) {
      if (element) {
        element.classList.remove('ui-hidden');
      }
    }

    function hideElement(element) {
      if (element) {
        element.classList.add('ui-hidden');
      }
    }

    function hideBootstrapMode() {
      hideElement(bootstrapMode);
    }

    function stopPolling() {
      if (pollTimer) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }
    }

    function setUploadError(message) {
      if (!uploadError) {
        return;
      }

      if (message) {
        uploadError.textContent = message;
        showElement(uploadError);
      } else {
        uploadError.textContent = '';
        hideElement(uploadError);
      }
    }

    function setCurrentDocument(element, prefix, documentName) {
      if (!element) {
        return;
      }

      if (!documentName) {
        element.innerHTML = '';
        hideElement(element);
        return;
      }

      element.innerHTML = prefix + ': <strong></strong>';
      var strong = element.querySelector('strong');
      if (strong) {
        strong.textContent = documentName;
      }
      showElement(element);
    }

    function showUploadState(options) {
      var errorMessage = options && options.errorMessage ? options.errorMessage : '';
      var currentDocumentName = options && options.currentDocumentName ? options.currentDocumentName : '';

      stopPolling();
      hideBootstrapMode();
      showElement(uploadMode);
      hideElement(processingMode);
      setUploadError(errorMessage);
      setCurrentDocument(currentDocument, 'Текущий документ', currentDocumentName);
      setCurrentDocument(processingCurrentDocument, 'Загруженный документ', '');

      if (uploadSubmitBtn) {
        uploadSubmitBtn.disabled = false;
        uploadSubmitBtn.textContent = 'Продолжить';
      }
    }

    function showProcessingState(message, currentDocumentName) {
      hideBootstrapMode();
      hideElement(uploadMode);
      showElement(processingMode);
      setUploadError('');

      if (currentDocumentName) {
        currentProcessingDocumentName = currentDocumentName;
      }

      setCurrentDocument(currentDocument, 'Текущий документ', '');
      setCurrentDocument(processingCurrentDocument, 'Загруженный документ', currentProcessingDocumentName);

      if (processingStatusText) {
        processingStatusText.textContent =
          message || 'Генерируем вопросы для интервью. Это может занять некоторое время...';
      }
    }

    function buildUploadRedirectUrl(errorMessage) {
      var url = new URL(config.uploadUrl, window.location.origin);
      if (errorMessage) {
        url.searchParams.set('error', errorMessage);
      }
      return url.toString();
    }

    function buildUploadStateUrl() {
      var url = new URL(config.uploadStateUrl, window.location.origin);
      var currentSearchParams = new URLSearchParams(window.location.search);

      currentSearchParams.forEach(function (value, key) {
        url.searchParams.set(key, value);
      });

      return url.toString();
    }

    async function fetchJson(url) {
      var response = await fetch(url, {
        method: 'GET',
        headers: {
          Accept: 'application/json'
        },
        credentials: 'same-origin',
        cache: 'no-store'
      });

      var payload = {};
      try {
        payload = await response.json();
      } catch (e) {
        payload = {};
      }

      return { response: response, payload: payload };
    }

    function getPayloadErrorMessage(payload, fallbackMessage) {
      return (
        payload.error_message ||
        payload.error ||
        payload.message ||
        fallbackMessage ||
        'Не удалось загрузить данные страницы.'
      );
    }

    async function loadInitialPageState() {
      try {
        var result = await fetchJson(buildUploadStateUrl());
        var payload = result.payload || {};

        if (payload.redirect_url) {
          window.location.href = payload.redirect_url;
          return;
        }

        if (payload.poll_interval_ms) {
          pollIntervalMs = Number(payload.poll_interval_ms) || config.defaultPollIntervalMs;
        }

        if (payload.page_state === 'processing') {
          showProcessingState(
            payload.processing_status_text || 'Генерируем вопросы для интервью. Это может занять некоторое время...',
            payload.current_document_name || ''
          );
          pollStatus();
          return;
        }

        showUploadState({
          errorMessage: payload.error_message || '',
          currentDocumentName: payload.current_document_name || ''
        });
      } catch (e) {
        showUploadState({
          errorMessage: '',
          currentDocumentName: ''
        });
      }
    }

    async function pollStatus() {
      try {
        var result = await fetchJson(config.statusUrl);
        var payload = result.payload || {};

        if (payload.status === 'success') {
          window.location.href = payload.redirect_url || config.interviewUrl;
          return;
        }

        if (payload.status === 'failure') {
          window.location.href =
            payload.redirect_url ||
            buildUploadRedirectUrl(getPayloadErrorMessage(payload, 'Не удалось сгенерировать вопросы.'));
          return;
        }

        showProcessingState(
          payload.status_text || 'Генерируем вопросы для интервью. Это может занять некоторое время...',
          currentProcessingDocumentName
        );
      } catch (e) {
        showProcessingState(
          'Проверяем статус генерации вопросов...',
          currentProcessingDocumentName
        );
      }

      pollTimer = window.setTimeout(pollStatus, pollIntervalMs);
    }

    async function submitUploadForm(event) {
      event.preventDefault();

      var selectedFile = fileInput && fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
      if (!selectedFile) {
        showUploadState({
          errorMessage: 'Выберите файл для загрузки.',
          currentDocumentName: ''
        });
        return;
      }

      currentProcessingDocumentName = selectedFile.name;

      if (uploadSubmitBtn) {
        uploadSubmitBtn.disabled = true;
        uploadSubmitBtn.textContent = 'Загружаем...';
      }

      showProcessingState(
        'Загружаем документ и запускаем генерацию вопросов...',
        currentProcessingDocumentName
      );

      stopPolling();

      try {
        var formData = new FormData(uploadForm);

        var response = await fetch(config.uploadUrl, {
          method: 'POST',
          body: formData,
          credentials: 'same-origin',
          redirect: 'follow'
        });

        if (response.redirected) {
          window.location.href = response.url;
          return;
        }

        if (!response.ok && response.status !== 202) {
          showUploadState({
            errorMessage: 'Не удалось загрузить документ. Попробуйте еще раз.',
            currentDocumentName: ''
          });
          return;
        }

        pollStatus();
      } catch (e) {
        showUploadState({
          errorMessage: 'Не удалось загрузить документ. Проверьте соединение и попробуйте снова.',
          currentDocumentName: ''
        });
      }
    }

    if (fileInput && selectedFileName) {
      fileInput.addEventListener('change', function () {
        var file = fileInput.files && fileInput.files[0];
        selectedFileName.textContent = file ? ('Выбран файл: ' + file.name) : '';
      });
    }

    if (uploadForm) {
      uploadForm.addEventListener('submit', submitUploadForm);
    }

    loadInitialPageState();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();