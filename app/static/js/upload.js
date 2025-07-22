const MAX_PRESENTATION_SIZE = 16;
let user_formats = []
let convertible_formats = ['pptx', 'ppt', 'odp']

$(function(){
    $("#alert").hide();
    $("#alert-warning").hide();
    $("#spinner").hide();
    let button_value = $('#button-submit')[0].value
    $('#upload-presentation-form').submit(function(event)
    {
        $("#spinner").show();
        event.preventDefault();
        $('#button-submit')[0].value = 'Обработка...';
        $('#button-submit').attr("disabled", true);

        fetch($(this)[0].action, 
        {
            method: "POST",
            follow: true,
            body: new FormData($(this)[0])
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            $("#spinner").hide();

            if (response.status == 413) {
                response.json().then(responseJson => {
                    $("#alert").show();
                    $("#error-text").html(responseJson["message"] || "Файл слишком большой или превышает лимит хранилища");
                });
                $('#button-submit')[0].value = button_value;
                
                return;
            }

            response.json().then(responseJson => {
                if (responseJson["message"] !== "OK"){
                    $("#alert").show();
                    $("#error-text").html(responseJson["message"]);
                    
                    $(this).trigger("reset");
                    $('#button-submit')[0].value = button_value
                    
                    return;
                }
            })
        });
    })

    fetch("/api/sessions/pres-formats/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] == "OK") {
                user_formats = responseJson['formats']
                $("#file-loading").attr('accept', `.${user_formats.join(', .')}`)
                if (user_formats.length == 1 && user_formats[0] == 'pdf')
                {
                    $("#format_notification").hide()
                    return
                }
                $('#user_allowed_formats')[0].textContent = user_formats.join(', ')
            }
        });
});


function fileLoadingOnChange() {
    $("#alert").hide();
    $("#alert-warning").hide();
    $("#spinner").hide();
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
        if (parts.length < 1 || !user_formats.includes(extension)) {
            $("#alert").show();
            $("#error-text").html(`Презентация должна быть в формате ${user_formats.join(', ')}!`);
            return;
        }
        if (file.size > MAX_PRESENTATION_SIZE * 1024 * 1024) {
            $("#alert").show();
            $("#error-text").html(`Размер файла с презентацией не должен превышать ${MAX_PRESENTATION_SIZE} мегабайт!`);
            return;
        }
        if (convertible_formats.includes(extension)) {
            $("#alert-warning").show();
            $("#warning-text").html("После загрузки презентация будет преобразована в PDF-формат (это может занять некоторое время). Для продолжения нажмите 'Начать тренировку'");
        }
        $("#button-submit").removeAttr("disabled");
    }
}
