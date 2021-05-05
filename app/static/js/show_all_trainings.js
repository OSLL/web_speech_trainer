function buildCurrentTrainingRow(trainingId, trainingJson) {
    options = { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }

    const currentTrainingRowElement = document.createElement("tr");

    const trainingIdElement = document.createElement("td");
    const trainingIdLink = document.createElement("a");
    trainingIdLink.href=`/trainings/statistics/${trainingId}/`;
    trainingIdLink.textContent = trainingId;
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

    const trainingUsernameElement = document.createElement("td");
    trainingUsernameElement.textContent = trainingJson["username"];
    currentTrainingRowElement.appendChild(trainingUsernameElement);

    const trainingFullNameElement = document.createElement("td");
    trainingFullNameElement.textContent = trainingJson["full_name"];
    currentTrainingRowElement.appendChild(trainingFullNameElement);

    const presentationRecordDurationElement = document.createElement("td");
    presentationRecordDurationElement.textContent = trainingJson["presentation_record_duration"];
    currentTrainingRowElement.appendChild(presentationRecordDurationElement);

    const trainingProcessingStartTimestampElement = document.createElement("td");
    timestamp_start = Date.parse(trainingJson["processing_start_timestamp"]);
    if (isNaN(timestamp_start) == false) {
        processing_start_time = new Date(timestamp_start);
        trainingProcessingStartTimestampElement.textContent = processing_start_time.toLocaleString("ru-RU", options);
    } else {
        trainingProcessingStartTimestampElement.textContent = "";
    }
    currentTrainingRowElement.appendChild(trainingProcessingStartTimestampElement);

    const trainingProcessingFinishTimestampElement = document.createElement("td");
    timestamp_finish = Date.parse(trainingJson["processing_finish_timestamp"]);
    if (isNaN(timestamp_finish) == false) {
        processing_finish_time = new Date(timestamp_finish);
        trainingProcessingFinishTimestampElement.textContent = processing_finish_time.toLocaleString("ru-RU", options);
    } else {
        trainingProcessingFinishTimestampElement.textContent = "";
    }
    currentTrainingRowElement.appendChild(trainingProcessingFinishTimestampElement);

    const trainingStatusElement = document.createElement("td");
    trainingStatusElement.textContent = trainingJson["training_status"];
    currentTrainingRowElement.appendChild(trainingStatusElement);

    const audioStatusElement = document.createElement("td");
    audioStatusElement.textContent = trainingJson["audio_status"];
    currentTrainingRowElement.appendChild(audioStatusElement);

    const presentationStatusElement = document.createElement("td");
    presentationStatusElement.textContent = trainingJson["presentation_status"];
    currentTrainingRowElement.appendChild(presentationStatusElement);

    const trainingPassBackStatusElement = document.createElement("td");
    trainingPassBackStatusElement.textContent = trainingJson["pass_back_status"];
    currentTrainingRowElement.appendChild(trainingPassBackStatusElement);

    const trainingScoreElement = document.createElement("td");
    if (trainingJson["score"] != null) {
        trainingScoreElement.textContent = trainingJson["score"].toFixed(2);
    }
    currentTrainingRowElement.appendChild(trainingScoreElement);

    return currentTrainingRowElement;
}

function buildAllTrainingsTable(trainingsJson) {
    if (trainingsJson["message"] !== "OK") {
        return;
    }
    const allTrainingsTable = document.getElementById("all-trainings-table");
    const titleRow = buildTitleRow(
        [
            "id тренировки",
            "Логин",
            "Имя",
            "Длительность аудиозаписи",
            "Начало обработки",
            "Конец обработки",
            "Статус тренировки",
            "Статус аудио",
            "Статус презентации",
            "Статус отправки в LMS",
            "Балл",
        ]
    );
    allTrainingsTable.appendChild(titleRow);

    Object.keys(trainingsJson["trainings"]).forEach(trainingId => {
        const currentTrainingRowElement = buildCurrentTrainingRow(trainingId, trainingsJson["trainings"][trainingId]);
        allTrainingsTable.appendChild(currentTrainingRowElement);
    });
}

function call_get_all_trainings(username, full_name) {
    fetch(`/api/trainings?username=${username}&full_name=${full_name}`)
        .then(response => response.json())
        .then(responseJson => buildAllTrainingsTable(responseJson));
}
