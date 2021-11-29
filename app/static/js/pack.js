$(function () {

    let alert_danger = $("#alert")
    let alert_warn = $("#alert-warning").hide();
    let alert_success = $("#alert-success").hide();
    let spinner = $("#spinner").hide();

    hideAll()

    function createCodeMirror(elem, mode){
        if (elem) {
            elem = CodeMirror.fromTextArea(elem,
                {
                    lineNumbers: true,
                    lineWrapping: true,
                    mode: mode
                }
            )
            elem.setSize(500, 200);
        }
    }

    let pack_parameters = document.getElementById("pack_parameters")
    createCodeMirror(pack_parameters, 'python')
    
    let pack_feedback = document.getElementById("pack_feedback")
    createCodeMirror(pack_feedback, 'htmlmixed')

    function get_text(index=0) {
        let editor = $('.CodeMirror')[index].CodeMirror;
        return editor.getValue()
    }

    $("#button-submit").click((e) => {
        hideAll()
        e.preventDefault()
        $("#spinner").show();
        let fd = new FormData();
        fd.append("parameters", get_text());
        fd.append("feedback", get_text(1));
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
        history.pushState(null, null, `/criteria_pack/${dictionary['name']}/`); 

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