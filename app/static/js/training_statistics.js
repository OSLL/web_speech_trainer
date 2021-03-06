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