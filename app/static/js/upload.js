const MAX_PRESENTATION_SIZE = 16;

$("#alert").hide();

function fileLoadingOnChange() {
    $("#alert").hide();
    if ($("#file-loading").prop("files").length < 1) {
        $("#alert").show();
        $("#error-text").html("Выберите файл!");
    } else {
        const file = $("#file-loading").prop("files")[0];
        let parts = file.name.split(".");
        if (parts.length <= 1 || parts.pop() !== "pdf") {
            $("#alert").show();
            $("#error-text").html("Презентация должна быть в формате PDF!");
            return;
        }
        if (file.size > MAX_PRESENTATION_SIZE * 1024 * 1024) {
            $("#alert").show();
            $("#error-text").html(`Размер файла с презентацией не должен превышать ${MAX_PRESENTATION_SIZE} мегабайт!`);
        }
    }
}
