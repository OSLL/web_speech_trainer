$('#alert').hide()

function onChange(){
    $('#alert').hide()
    if ($('#file-loading').prop('files').length < 1) {
        $('#alert').show()
        str = "Select file!"
        $('#error-text').html(str)
    } else {
        var file = $('#file-loading').prop('files')[0]
        parts = file.name.split('.')
        if (parts.length <= 1 || parts.pop() != 'pdf'){
                $('#alert').show()
                str = "Presentation file should be a pdf file!"
                $('#error-text').html(str)
                return
        }
        if (file.size > 10000000){
            $('#alert').show()
                str = "Presentation file should not exceed 10MB"
                $('#error-text').html(str)
        }
    }
}