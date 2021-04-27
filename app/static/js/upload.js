const MAX_PRESENTATION_SIZE = 16;

$('#alert').hide()

function onChange() {
    $('#alert').hide()
    if ($('#file-loading').prop('files').length < 1) {
        $('#alert').show()
        str = "Выберете файл!"
        $('#error-text').html(str)
    } else {
        var file = $('#file-loading').prop('files')[0]
        parts = file.name.split('.')
        if (parts.length <= 1 || parts.pop() != 'pdf') {
            $('#alert').show()
            str = "Презентация должна быть в формате PDF!"
            $('#error-text').html(str)
            return
        }
        if (file.size > MAX_PRESENTATION_SIZE *1024*1024) {
            $('#alert').show()
            str = `Размер файла с презентацией не должен привышать ${MAX_PRESENTATION_SIZE}MB`
            $('#error-text').html(str)
        }
    }
}
