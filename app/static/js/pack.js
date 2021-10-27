$(function () {

    let alert_danger = $("#alert")
    let alert_warn = $("#alert-warning").hide();
    let alert_success = $("#alert-success").hide();
    let spinner = $("#spinner").hide();

    hideAll()


    let pack_parameters = document.getElementById("pack_parameters")
    if (pack_parameters) {
        pack_parameters = CodeMirror.fromTextArea(pack_parameters,
            {
                lineNumbers: true,
                lineWrapping: true,
                mode: "python"
            }
        )
        pack_parameters.setSize(500, 150);
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
    
    function updatе(dictionary){
        $("#pack_name").text(dictionary['name'])
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