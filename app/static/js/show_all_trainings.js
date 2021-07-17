function get_time_string(timestamp){
    options = { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }
    if (!isNaN(timestamp)) {
        processing_time = new Date(timestamp);
        return processing_time.toLocaleString("ru-RU", options);
    } else {
        return "";
    }
}

function buildCurrentTrainingRow(trainingId, trainingJson) {

    const currentTrainingRowElement = document.createElement("tr");

    const trainingIdElement = document.createElement("td");
    const trainingIdLink = document.createElement("a");
    trainingIdLink.href=`/trainings/statistics/${trainingId}/`;
    trainingIdLink.textContent = "..." + String(trainingId).slice(-5);
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

    const trainingAttemptIdElement = document.createElement("td");
    if(trainingJson["task_attempt_id"] !== "undefined" && trainingJson["message"] === "OK"){
        trainingAttemptIdElement.textContent = "..." + String(trainingJson["task_attempt_id"]).slice(-5);
    }
    currentTrainingRowElement.appendChild(trainingAttemptIdElement);

    const trainingUsernameElement = document.createElement("td");
    const trainingUsernameLink = document.createElement("a");
    trainingUsernameLink.href = `/show_all_trainings/?username=${trainingJson["username"]}&full_name=${trainingJson["full_name"]}`;
    trainingUsernameLink.textContent = trainingJson["username"];
    trainingUsernameElement.appendChild(trainingUsernameLink);
    currentTrainingRowElement.appendChild(trainingUsernameElement);

    const trainingFullNameElement = document.createElement("td");
    trainingFullNameElement.textContent = trainingJson["full_name"];
    currentTrainingRowElement.appendChild(trainingFullNameElement);

    const presentationRecordDurationElement = document.createElement("td");
    presentationRecordDurationElement.textContent = trainingJson["presentation_record_duration"];
    currentTrainingRowElement.appendChild(presentationRecordDurationElement);

    const trainingProcessingStartTimestampElement = document.createElement("td");
    timestamp_start = Date.parse(trainingJson["processing_start_timestamp"]);
    trainingProcessingStartTimestampElement.textContent = get_time_string(timestamp_start);
    currentTrainingRowElement.appendChild(trainingProcessingStartTimestampElement);

    const trainingProcessingFinishTimestampElement = document.createElement("td");
    timestamp_finish = Date.parse(trainingJson["processing_finish_timestamp"]);
    trainingProcessingFinishTimestampElement.textContent = get_time_string(timestamp_finish);
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

    const presentationFileIdElement = document.createElement("td");
    if(trainingJson["presentation_file_id"] !== "undefined" && trainingJson["message"] === "OK"){
        const presentationFileIdLink = document.createElement("a");
        presentationFileIdLink.textContent = "..." + String(trainingJson["presentation_file_id"]).slice(-5);
        presentationFileIdLink.href = `/api/files/presentations/by-training/${trainingId}/`;
        presentationFileIdLink.target = "_blank";
        presentationFileIdElement.appendChild(presentationFileIdLink);
    }
    currentTrainingRowElement.appendChild(presentationFileIdElement);

    const recordingElement = document.createElement("td");
    if(trainingJson["presentation_record_file_id"] === "None" || trainingJson["message"] !== "OK") {
        recordingElement.textContent = "Аудиозапись отсутствует";
    } else {
        const recordingAudio = document.createElement("audio");
        recordingAudio.controls = true;
        recordingAudio.src = `/api/files/presentation-records/${trainingJson["presentation_record_file_id"]}/`;
        recordingElement.appendChild(recordingAudio);
    }
    currentTrainingRowElement.appendChild(recordingElement);

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
            "id попытки",
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
            "Презентация",
            "Аудиозапись"
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
