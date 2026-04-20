(function () {
  function init() {
    const config = window.INTERVIEW_UPLOAD_DATA || {};
    const uploadMode = document.getElementById('upload-mode');
    const processingMode = document.getElementById('processing-mode');
    const uploadError = document.getElementById('upload-error');
    const processingStatusText = document.getElementById('processing-status-text');
    const currentDocument = document.getElementById('current-document');
    const fileInput = document.getElementById('document');
    const selectedFileName = document.getElementById('selected-file-name');
    const uploadForm = document.getElementById('upload-form');
    const uploadSubmitBtn = document.getElementById('upload-submit-btn');

    let pollTimer = null;

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

    function setUploadError(message) {
      if (!uploadError) {
        return;
      }

      if (message) {
        uploadError.textContent = message;
        showElement(uploadError);
        return;
      }

      uploadError.textContent = '';
      hideElement(uploadError);
    }

    function showUploadState(message) {
      if (pollTimer) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }

      showElement(uploadMode);
      hideElement(processingMode);
      setUploadError(message || '');

      if (fileInput) {
        fileInput.value = '';
      }

      if (selectedFileName) {
        selectedFileName.textContent = '';
      }

      if (uploadSubmitBtn) {
        uploadSubmitBtn.disabled = false;
        uploadSubmitBtn.textContent = 'Продолжить';
      }

      if (currentDocument && !currentDocument.textContent.trim()) {
        hideElement(currentDocument);
      }
    }

    function showProcessingState(message) {
      hideElement(uploadMode);
      showElement(processingMode);

      if (processingStatusText) {
        processingStatusText.textContent =
          message || 'Пожалуйста, подождите. Мы анализируем документ и готовим вопросы.';
      }
    }

    function buildUploadRedirectUrl(errorMessage) {
      const baseUrl = config.uploadUrl || '/interview/upload/';
      const url = new URL(baseUrl, window.location.origin);

      if (errorMessage) {
        url.searchParams.set('error', errorMessage);
      }

      return url.toString();
    }

    async function pollStatus() {
      try {
        const response = await fetch(config.statusUrl, {
          method: 'GET',
          headers: {
            Accept: 'application/json',
          },
          credentials: 'same-origin',
          cache: 'no-store',
        });

        let payload = {};
        try {
          payload = await response.json();
        } catch (error) {
          payload = {};
        }

        if (payload.status === 'success') {
          window.location.href = payload.redirect_url || config.interviewUrl || '/interview/';
          return;
        }

        if (payload.status === 'failure') {
          window.location.href =
            payload.redirect_url || buildUploadRedirectUrl(payload.error || 'Не удалось сгенерировать вопросы.');
          return;
        }

        showProcessingState(
          payload.status_text || 'Генерируем вопросы для интервью. Это может занять некоторое время...'
        );
      } catch (error) {
        showProcessingState('Проверяем статус генерации вопросов...');
      }

      pollTimer = window.setTimeout(pollStatus, config.pollIntervalMs || 2000);
    }

    if (fileInput && selectedFileName) {
      fileInput.addEventListener('change', function () {
        const file = fileInput.files && fileInput.files[0];
        selectedFileName.textContent = file ? `Выбран файл: ${file.name}` : '';
      });
    }

    if (uploadForm && uploadSubmitBtn) {
      uploadForm.addEventListener('submit', function () {
        uploadSubmitBtn.disabled = true;
        uploadSubmitBtn.textContent = 'Загружаем...';
      });
    }

    if (config.isProcessing) {
      showProcessingState();
      pollStatus();
    } else {
      showUploadState(uploadError ? uploadError.textContent.trim() : '');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();