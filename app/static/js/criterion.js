$(function () {

    let alert_danger = $("#alert")
    let alert_warn = $("#alert-warning").hide();
    let alert_success = $("#alert-success").hide();
    let spinner = $("#spinner").hide();

    hideAll()

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
        criterion_parameters.setSize(500, 150);
    }

    function get_text() {
        let editor = $('.CodeMirror')[0].CodeMirror;
        return editor.getValue()
    }

    $("#button-submit").click((e) => {
        hideAll()
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
                    updatе(responseJson)
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

    function updatе(dictionary){
        $("#criterion_name").text(dictionary['name'])
        history.pushState(null, null, `/criterion/${dictionary['name']}/`); 

        alert_success.text(`Updated: ${new Date(dictionary['time'])}`)
        alert_success.show()
    }

    function hideAll(){
        alert_danger.hide();
        alert_warn.hide();
        alert_success.hide();
        spinner.hide();
    }
})