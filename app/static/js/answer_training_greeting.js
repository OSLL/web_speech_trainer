document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-loading');
    const submitButton = document.getElementById('button-submit');

    fileInput.addEventListener('change', function() {
        if (fileInput.files.length > 0) {
            submitButton.removeAttribute('disabled');
        } else {
            submitButton.setAttribute('disabled', 'true');
        }
    });
});