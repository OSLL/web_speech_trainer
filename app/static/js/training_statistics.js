document.addEventListener("DOMContentLoaded", function() {
    fetch(`/get_current_task_attempt`)
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
                = "Баллы за предыдущие тренировки: " + response["current_points"];
            let next_training = document.getElementById("next-training");
            next_training.style.visibility = "visible";
            next_training.style.fontSize = "14pt";
        });
    document.getElementById("next-training-button").onclick = function () {
        window.location.href = `/training_greeting`;
    }
});

function buildAudioSlideTranscriptionRow(slideNumber, words) {
    const currentSlideRowElement = document.createElement('tr');

    const slideNumberElement = document.createElement('td');
    slideNumberElement.textContent = slideNumber;
    currentSlideRowElement.appendChild(slideNumberElement);

    const transcriptionElement = document.createElement('td');
    transcriptionElement.textContent = words;
    currentSlideRowElement.appendChild(transcriptionElement);

    return currentSlideRowElement;
}

function buildPerSlideAudioTranscriptionTable(audioTranscriptionJson) {
    const perSlideAudioTranscriptionTable = document.getElementById("per-slide-audio-transcription-table");
    const titleRow = buildTitleRow(["Номер слайда", "Транскрипция"]);
    perSlideAudioTranscriptionTable.appendChild(titleRow);
    for (let i = 0; i < audioTranscriptionJson.length; i++) {
        perSlideAudioTranscriptionTable.appendChild(
            buildAudioSlideTranscriptionRow(i + 1, audioTranscriptionJson[i])
        );
    }
}

function setPerSlideAudioTranscriptionTable(trainingId) {
    fetch(`/get_audio_transcription?trainingId=${trainingId}`)
        .then(response => response.json())
        .then(responseJson => buildPerSlideAudioTranscriptionTable(responseJson));
}

function setVerdict(s) {
    document.getElementById('verdict').innerText = `${s}`;
}