const MAX_PRESENTATION_SIZE = 16;
let user_formats = []

$(function(){
    $("#alert").hide();
    $("#alert-warning").hide();

    $('#upload-presentation-form').submit(function()
    {
        $('#button-submit').value = 'Обработка...';
        $('#button-submit').attr("disabled", true);
    })

    fetch("/api/sessions/pres-formats/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] == "OK") {
                user_formats = responseJson['formats']
                $('#user_allowed_formats')[0].textContent = user_formats.join(', ')
            }
        });
});


function fileLoadingOnChange() {
    $("#alert").hide();
    $("#alert-warning").hide();
    $("#button-submit").attr("disabled", true);
    if ($("#file-loading").prop("files").length < 1) {
        $("#alert").show();
        $("#error-text").html("Выберите файл!");
    } else {
        const file = $("#file-loading").prop("files")[0];
        let parts = file.name.split(".");
        let extension = parts.pop().toLowerCase();
        console.log(`File extension ${extension}`)
        /* TODO: use list with user-allowed extensions */
        if (parts.length < 1 || !['pdf', 'pptx', 'ppt', 'odp'].includes(extension)) {
            $("#alert").show();
            $("#error-text").html(`Презентация должна быть в формате ${user_formats.join(', ')}!`);
            return;
        }
        if (file.size > MAX_PRESENTATION_SIZE * 1024 * 1024) {
            $("#alert").show();
            $("#error-text").html(`Размер файла с презентацией не должен превышать ${MAX_PRESENTATION_SIZE} мегабайт!`);
            return;
        }
        if (['pptx', 'ppt', 'odp'].includes(extension)) {
            $("#alert-warning").show();
            $("#warning-text").html("Презентация будет преобразована в PDF-формат. Это может занять некоторое время!");
        }
        $("#button-submit").removeAttr("disabled");
    }
}
