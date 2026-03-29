(function () {
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

    if (currentDocument) {
      currentDocument.textContent = '';
      hideElement(currentDocument);
    }

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
  }

  function showProcessingState(message) {
    hideElement(uploadMode);
    showElement(processingMode);
    if (processingStatusText) {
      processingStatusText.textContent = message || 'Пожалуйста, подождите. Мы анализируем документ и готовим вопросы.';
    }
  }

  async function pollStatus() {
    try {
      const response = await fetch(config.statusUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        },
        credentials: 'same-origin'
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
        showUploadState(payload.error || 'Не удалось сгенерировать вопросы. Загрузите документ заново.');
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
      selectedFileName.textContent = file ? ('Выбран файл: ' + file.name) : '';
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
  }
})();
