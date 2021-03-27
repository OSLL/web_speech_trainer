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

    const trainingDatetimeElement = document.createElement('td');
    trainingDatetimeElement.textContent = trainingJson['datetime'];
    currentTrainingRowElement.appendChild(trainingDatetimeElement);

    const trainingScoreElement = document.createElement('td');
    let score = trainingJson['score'];
    if (score !== null) {
        trainingScoreElement.textContent = trainingJson['score'];
    } else {
        trainingScoreElement.textContent = '...';
    }
    currentTrainingRowElement.appendChild(trainingScoreElement);

    return currentTrainingRowElement;
}

function buildAllTrainingsTable(trainingsJson) {
    const allTrainingsTable = document.getElementById('all-trainings-table');
    const titleRow = buildTitleRow(['id', 'Логин', 'Имя', 'Время', 'Результат']);
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
