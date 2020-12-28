function buildCurrentTrainingRow(trainingId, trainingJson) {
    const currentTrainingRowElement = document.createElement('tr');

    const trainingIdElement = document.createElement('td');
    const trainingIdLink = document.createElement('a');
    trainingIdLink.href=`/training_statistics/${trainingId}/`;
    trainingIdLink.textContent = trainingId;
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

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
    const titleRow = buildTitleRow(['id', 'Время', 'Результат']);
    allTrainingsTable.appendChild(titleRow);

    Object.keys(trainingsJson).forEach(trainingId => {
        const currentTrainingRowElement = buildCurrentTrainingRow(trainingId, trainingsJson[trainingId]);
        allTrainingsTable.appendChild(currentTrainingRowElement);
    });
}

function call_get_all_trainings() {
    fetch('/get_all_trainings')
        .then(response => response.json())
        .then(responseJson => buildAllTrainingsTable(responseJson));
}
