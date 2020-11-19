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

function buildTitleRow() {
    const titleRowElement = document.createElement('tr');

    const trainingIdElement = document.createElement('th');
    trainingIdElement.textContent = 'id';
    titleRowElement.appendChild(trainingIdElement);

    const trainingDatetimeElement = document.createElement('th');
    trainingDatetimeElement.textContent = 'Время';
    titleRowElement.appendChild(trainingDatetimeElement);

    const trainingScoreElement = document.createElement('th');
    trainingScoreElement.textContent = 'Результат';
    titleRowElement.appendChild(trainingScoreElement);

    return titleRowElement;

}

function buildAllTrainingsTable(trainingsJson) {
    const allTrainingsTable = document.getElementById('all-trainings-table');
    const titleRow = buildTitleRow();
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
