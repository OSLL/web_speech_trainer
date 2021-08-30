$(function () {

    $("#alert").hide();
    $("#alert-warning").hide();
    $("#spinner").hide();

    let criterions = {}

    fetch("/api/criterion/structures")
        .then(response => response.json())
        .then(responseJson => {
            criterions = responseJson
            update_structure() 
        })

    $("#base_criterion").on("change", update_structure)

    let criterion_parameters = document.getElementById("criterion_parameters")
    if (criterion_parameters) {
        criterion_parameters = CodeMirror.fromTextArea(criterion_parameters,
            {
                lineNumbers: true,
                lineWrapping: true,
                mode: "python"
            }
        )
    }

    function get_text() {
        let editor = $('.CodeMirror')[0].CodeMirror;
        return editor.getValue()
    }

    $("#button-submit").click((e) => {
        e.preventDefault()
        $("#spinner").show();
        let fd = new FormData();
        fd.append("parameters", get_text());
        fd.append("base_criterion", $("#base_criterion")[0].value);
        fetch(`/api${window.location.pathname}`, { method: "POST", body: fd })
            .then(response => response.json())
            .then(responseJson => {
                $("#spinner").hide();
                if (responseJson["message"] === "OK") {
                    location.href = `/criterion/${responseJson['id']}/`;
                }
                else {
                    $("#alert").show();
                    $("#error-text").html(responseJson["message"].replace("\n", "<br>"));
                }
            });
    })
    
    function update_structure(){
        let a = $("#base_criterion")
        let criterion = a.val()
        $("#criterion_structure").text(criterions[criterion])
    }
})