function buildCurrentTrainingRow(trainingId, trainingJson) {
    const currentTrainingRowElement = document.createElement('tr');

    const trainingIdElement = document.createElement('td');
    const trainingIdLink = document.createElement('a');
    trainingIdLink.href=`/training_statistics/${trainingId}/`;
    trainingIdLink.textContent = trainingId;
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

    const trainingUsernameElement = document.createElement('td');
    trainingUsernameElement.textContent = trainingJson['username'];
    currentTrainingRowElement.appendChild(trainingUsernameElement);

    const trainingFullNameElement = document.createElement('td');
    trainingFullNameElement.textContent = trainingJson['full_name'];
    currentTrainingRowElement.appendChild(trainingFullNameElement);

    const presentationRecordDurationElement = document.createElement('td');
    presentationRecordDurationElement.textContent = trainingJson['presentation_record_duration'];
    currentTrainingRowElement.appendChild(presentationRecordDurationElement);

    const trainingProcessingStartTimestampElement = document.createElement('td');
    trainingProcessingStartTimestampElement.textContent = trainingJson['processing_start_timestamp'];
    currentTrainingRowElement.appendChild(trainingProcessingStartTimestampElement);

    const trainingProcessingFinishTimestampElement = document.createElement('td');
    trainingProcessingFinishTimestampElement.textContent = trainingJson['processing_finish_timestamp'];
    currentTrainingRowElement.appendChild(trainingProcessingFinishTimestampElement);

    const trainingStatusElement = document.createElement('td');
    trainingStatusElement.textContent = trainingJson['training_status'];
    currentTrainingRowElement.appendChild(trainingStatusElement);

    const audioStatusElement = document.createElement('td');
    audioStatusElement.textContent = trainingJson['audio_status'];
    currentTrainingRowElement.appendChild(audioStatusElement);

    const presentationStatusElement = document.createElement('td');
    presentationStatusElement.textContent = trainingJson['presentation_status'];
    currentTrainingRowElement.appendChild(presentationStatusElement);

    const trainingPassBackStatusElement = document.createElement('td');
    trainingPassBackStatusElement.textContent = trainingJson['pass_back_status'];
    currentTrainingRowElement.appendChild(trainingPassBackStatusElement);

    const trainingScoreElement = document.createElement('td');
    trainingScoreElement.textContent = trainingJson['score'];
    currentTrainingRowElement.appendChild(trainingScoreElement);

    return currentTrainingRowElement;
}

function buildAllTrainingsTable(trainingsJson) {
    const allTrainingsTable = document.getElementById('all-trainings-table');
    const titleRow = buildTitleRow(
        [
            'id тренировки',
            'Логин',
            'Имя',
            'Длительность аудиозаписи',
            'Начало обработки',
            'Конец обработки',
            'Статус тренировки',
            'Статус аудио',
            'Статус презентации',
            'Статус отправки в LMS',
            'Балл',
        ]
    );
    allTrainingsTable.appendChild(titleRow);

    Object.keys(trainingsJson).forEach(trainingId => {
        const currentTrainingRowElement = buildCurrentTrainingRow(trainingId, trainingsJson[trainingId]);
        allTrainingsTable.appendChild(currentTrainingRowElement);
    });
}

function call_get_all_trainings(username, full_name) {
    fetch(`/get_all_trainings?username=${username}&full_name=${full_name}`)
        .then(response => response.json())
        .then(responseJson => buildAllTrainingsTable(responseJson));
}
