let gumStream,
    recorder,
    input,
    encodeAfterRecord,
    currentTimestamp,
    timer;

function startRecording() {
    console.log("call startRecording(). Try to call navigator.mediaDevices.getUserMedia");
    console.log("navigator", navigator);
    console.log("navigator.mediaDevices", navigator.mediaDevices);
    $("#alert").hide()
    $("#record-contain").show();
    navigator.mediaDevices.getUserMedia({audio: true, video: false}).then(function (stream) {
        currentTimestamp = Date.now();
        $("#tutorial")[0].style = "visibility: hidden; font-size: 0; margin-bottom: 0";
        var model_time = 3;
        $("#model-time").html(`До начала записи: ${model_time} сек.`);
        $("#model-timer").show();
        model_timer = setInterval(() => {
            if (model_time == 0) {
                clearInterval(model_timer);
                $("#model-timer").hide();
            }
            model_time--;
            $("#model-time").html(`До начала записи: ${model_time} сек.`);

        }, 1000)
        setTimeout(function () {
            callShowPage();
            maxTime = undefined;
            /*fetch(`/api/criteria/${trainingId}/SpeechDurationCriterion/maximal_allowed_duration/`)
                .then(response => response.json())
                .then(function (data) {
                    if (data["message"] === "OK") {
                        maxTime = data["parameterValue"];
                    }
                })*/
            time = 0;
            $("#timer").show();
            timer = setInterval(function () {
                seconds = time % 60;
                if (seconds < 10) {
                    seconds = `0${seconds}`;
                }
                minuts = Math.trunc(time / 60 % 60);
                if (minuts < 10) {
                    minuts = `0${minuts}`;
                }
                hour = time / 60 / 60 % 60;
                let strTimer = `Время тренировки: ${Math.trunc(hour)}:${minuts}:${seconds}`;
                $("#timer").html(strTimer);
                if (maxTime && time >= maxTime) {
                    $("#timer").css("color", "red");
                }
                time++;
            }, 1000);
        }, 3000);

        let audioContext = new window.AudioContext();
        gumStream = stream;
        input = audioContext.createMediaStreamSource(stream);

        startMicVisualizer(stream, audioContext);

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
        console.log('Error on calling avigator.mediaDevices.getUserMedia')
        console.log(err)
        $("#alert").show();
        $("#error-text").html("Микрофон не доступен!");
    });
}

function stopRecording() {
    if (confirm('Завершить тренировку?') === true) {
        window.onbeforeunload = null;
        clearInterval(timer)
        $("#timer").hide();
        gumStream.getAudioTracks()[0].stop();
        $("#record")[0].disabled = false;
        $("#record-processing")[0].style = "visibility: visible; font-size: 36px";
        recorder.finishRecording();
    }
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
    window.onbeforeunload = function(){
        return "Do you really want to close?";
    };
});

function startMicVisualizer (stream, audioContext) {
    const canvasElement = document.querySelector("#mic-visualizer-canvas");
    const canvasVisializerCxt = canvasElement.getContext("2d");
    const volumeLevelElement = document.querySelector("#volume-level-box");

    const audioStream = audioContext.createMediaStreamSource( stream );
    const analyser = audioContext.createAnalyser();
    const fftSize = 128;

    analyser.fftSize = fftSize;
    audioStream.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;

    let frequencyArray = new Uint8Array(bufferLength);

    const setUpCanvas = function () {
        canvasVisializerCxt.fillStyle = "rgb(255 255 255)";
        canvasVisializerCxt.fillRect(0, 0, canvasElement.width, canvasElement.height);
      
        canvasVisializerCxt.lineWidth = 1.5;
        canvasVisializerCxt.strokeStyle = "rgb(0 0 0)";
      
        canvasVisializerCxt.beginPath();
    }

    const doDraw = function () {
        requestAnimationFrame(doDraw);

        setUpCanvas();

        const sliceWidth = (canvasElement.width * 1.0) / (bufferLength + 1);

        canvasVisializerCxt.moveTo(0, canvasElement.height / 2);

        let x = 0 + sliceWidth;

        analyser.getByteFrequencyData(frequencyArray);

        let direction = 1;

        for (let i = 0; i < bufferLength; i++) {
            const v = frequencyArray[i] / (canvasElement.height * 2);
            const y = (v * canvasElement.height) / 2;
        
            canvasVisializerCxt.lineTo(x, canvasElement.height / 2 + y * direction);
        
            x += sliceWidth;
            direction *= -1;
        }

        canvasVisializerCxt.lineTo(canvasElement.width, canvasElement.height / 2);
        canvasVisializerCxt.stroke();
    }
    
    const showVolume = function () {
        setTimeout(showVolume, 500);

        analyser.getByteFrequencyData(frequencyArray);
        let total = 0

        for(let i = 0; i < bufferLength; i++) {
            let x = frequencyArray[i];
            total += x * x;
        }

        const rms = Math.sqrt(total / bufferLength);
        let db = 20 * ( Math.log(rms) / Math.log(10) );

        db = Math.max(db, 0);

        let status = "";

        // добавить эти поля в локаль
        if (db == 0) {
            status = "Ваш микрофон не работает";
        }
        else if (db <= 35) { // или другое значение/проверка (например только по средним частотам)
            status = "Пожалуйста, говорите громче"; // проверить, что пауза достаточно продолжительна
        }

        volumeLevelElement.innerHTML = `db: ${db.toFixed(1)} ${status}`;
    }

    doDraw();
    showVolume();
}