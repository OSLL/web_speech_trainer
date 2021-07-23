function buildCurrentAttemptStatistics() {
    const trainingId = window.location.pathname.split("/")[3];
    fetch(`/api/task-attempts/?training_id=${trainingId}`)
        .then(response => response.json())
        .then(response => {
            let trainingNumber = response["training_number"];
            let attemptCount = response["attempt_count"];
            if (response === {} || trainingNumber === attemptCount) {
                return;
            }
            document.getElementById("training-number").textContent
                = "Номер тренировки: " + response["training_number"] + " / " + response["attempt_count"];
            document.getElementById("current-points").textContent
                = "Сумма баллов за предыдущие тренировки: " + response["current_points_sum"].toFixed(2);
            let next_training = document.getElementById("next-training");
            next_training.style.visibility = "visible";
            next_training.style.fontSize = "14pt";
        });
}

document.addEventListener("DOMContentLoaded", function() {
    buildCurrentAttemptStatistics();
    document.getElementById("next-training-button").onclick = function () {
        window.location.href = `/training_greeting`;
    }
});

function configureAudio(info) {
    var audio = $('#presentation-record')[0]
    audio.addEventListener('timeupdate', function ()
        {
            let page_num = parseInt($("#page_num")[0].textContent, 10)
            for (let i = page_num-1; i < info.length-1; i++) {
                if (info[i] < this.currentTime && this.currentTime < info[i+1])
                {
                    setPage(i+1, info);
                    break;
                }
            }
            if (this.currentTime > info[info.length-1])
                setPage(info.length, info);
            console.log(this.currentTime);
        }
    )
}

function setAudioTime(time){
    var audio = $('#presentation-record')[0];
    audio.currentTime = time;
    changeURLByParam('time', time);
}

function buildAudioSlideTranscriptionRow(slideNumber, words) {
    const currentSlideRowElement = document.createElement("tr");

    const slideNumberElement = document.createElement("td");
    slideNumberElement.textContent = slideNumber;
    currentSlideRowElement.appendChild(slideNumberElement);

    const transcriptionElement = document.createElement("td");
    transcriptionElement.textContent = words;
    currentSlideRowElement.appendChild(transcriptionElement);

    return currentSlideRowElement;
}

function buildPerSlideAudioTranscriptionTable(audioTranscriptionJson) {
    if (audioTranscriptionJson["message"] !== "OK") {
        return;
    }
    const perSlideAudioTranscriptionTable = document.getElementById("per-slide-audio-transcription-table");
    const titleRow = buildTitleRow(["Номер слайда", "Транскрипция"]);
    perSlideAudioTranscriptionTable.appendChild(titleRow);
    for (let i = 0; i < audioTranscriptionJson["audio_transcription"].length; i++) {
        perSlideAudioTranscriptionTable.appendChild(
            buildAudioSlideTranscriptionRow(i + 1, audioTranscriptionJson["audio_transcription"][i])
        );
    }
}

function setPerSlideAudioTranscriptionTable(trainingId) {
    const params = new URLSearchParams(window.location.search);
    if (params.get("transcription")) {
        fetch(`/api/audio/transcriptions/${trainingId}/`)
            .then(response => response.json())
            .then(responseJson => buildPerSlideAudioTranscriptionTable(responseJson));
    }
}

function setVerdict(s) {
    document.getElementById("verdict").innerText = `${s}`;
}

function setCriteriaResults(s) {
    document.getElementById("criteria-results").innerText = `${s}`;
}

function setRecognizedInfo(slides){
    console.log(slides)
}

function renderPageButtons(info){
    var count = info.length;
    var button_div = $('#page_buttons')[0]
    for (let i = 1; i <= count; i++) {
        var button = $(`<button id="page${i}" name="audio_control_button" >${i}</button>`)[0];
        $(button).click(function() {
            setAudioTime(info[i-1]) 
            setPage(i)
        })
        button_div.append(button);
    }
}

function changeTrainingStatsURL() {
    //parse url
    let params = location.search.replace('?','').split('&')
                    .reduce(
                        function(p,e) {
                            let a = e.split('=');
                            p[decodeURIComponent(a[0])] = decodeURIComponent(a[1]);
                            return p;
                        },
                        {}  
                    );
    
    if('time' in params && parseFloat(params['time'])){
        setAudioTime(parseFloat(params['time'])) 
    }
    
    if ('page' in params && parseInt(params['page'])){
        setPage(parseInt(params['page'], 10))
    }
}
