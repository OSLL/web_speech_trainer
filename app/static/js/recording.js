let gumStream,
    recorder,
    input,
    encodeAfterRecord,
    currentTimestamp,
    timer;

function startRecording() {
    navigator.mediaDevices.getUserMedia({audio: true, video: false}).then(function (stream) {
        currentTimestamp = Date.now();
        $("#tutorial")[0].style = "visibility: hidden; font-size: 0";
        $("#denoising-note")[0].style = "visibility: visible; font-size: 14";
        setTimeout(function () {
            callShowPage();
            maxTime = undefined;
            fetch(`/api/criteria/${trainingId}/SpeechDurationCriterion/maximal_allowed_duration/`)
                .then(response => response.json())
                .then(function (data) {
                    if (data["message"] === "OK") {
                        maxTime = data["parameterValue"];
                    }
                })
            time = 0;
            $("#timer").show();
            timer = setInterval(function () {
                seconds = time % 60;
                if (seconds < 10) {
                    seconds = `0${seconds}`;
                }
                minuts = time / 60 % 60;
                if (minuts < 10) {
                    minuts = `0${Math.trunc(minuts)}`;
                }
                hour = time / 60 / 60 % 60;
                let strTimer = `Время тренировки: ${Math.trunc(hour)}:${minuts}:${seconds}`;
                $("#timer").html(strTimer);
                if (maxTime && time >= maxTime) {
                    $("#timer").css("color", "red");
                }
                time++;
            }, 1000)
            $("#denoising-note")[0].style = "visibility: hidden; font-size: 0";
        }, 3000);
        let audioContext = new window.AudioContext();
        gumStream = stream;
        input = audioContext.createMediaStreamSource(stream);
        recorder = new WebAudioRecorder(input, {
            workerDir: "/static/js/libraries/WebAudioRecorder.js/",
            encoding: "mp3",
        });
        recorder.onComplete = function (recorder, blob) {
            $("#record-processing")[0].style = "visibility: hidden; font-size: 0";
            window.onbeforeunload = null;
            callAddPresentationRecord(blob);
        }
        recorder.setOptions({
            timeLimit: 3600,
            encodeAfterRecord: encodeAfterRecord,
            mp3: {bitRate: 160}
        });
        recorder.startRecording();
        $("#next")[0].disabled = false;
        $("#record")[0].disabled = true;
        $("#done")[0].disabled = false;
    }).catch( err => {
        $("#alert").show();
        $("#error-text").html("Микрофон не доступен!");
    });
}

function stopRecording() {
    clearInterval(timer)
    $("#timer").hide();
    gumStream.getAudioTracks()[0].stop();
    $("#record")[0].disabled = false;
    $("#record-processing")[0].style = "visibility: visible; font-size: 14px";
    window.onbeforeunload = function() {
        return false;
    }
    recorder.finishRecording();
}

function callAddPresentationRecord(blob) {
    let fd = new FormData();
    fd.append("presentationRecord", blob);
    fd.append("presentationRecordDuration", ((Date.now() - currentTimestamp) / 1000).toString());
    fetch(`/api/trainings/presentation-records/${trainingId}/`, {method: "POST", body: fd})
    .then(response => response.json())
    .then(responseJson => {
        if (responseJson["message"] === "OK") {
            fetch(`/api/trainings/${trainingId}/`, {method: "POST"})
                .then(response => response.json())
                .then(innerResponseJson => {
                    if (innerResponseJson["message"] === "OK") {
                        location.href = `/trainings/statistics/${trainingId}/`;
                    }
                });
        }
    });
}

$(document).ready(function () {
    $("#timer").hide();
    encodeAfterRecord = true;
    $("#record").click(startRecording);
    $("#done").click(stopRecording);
    $("#record-processing")[0].style = "visibility: hidden; font-size: 0";
    window.onbeforeunload = null;
    $("#denoising-note")[0].style = "visibility: hidden; font-size: 0";
});
