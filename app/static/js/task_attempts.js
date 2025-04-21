function getTrainingsTable(trainingScores, isPassedBack) {
    const trainingsTable = {}; 

    Object.keys(trainingScores).forEach(trainingId => {
        if (trainingsTable[trainingId] === undefined) {
            trainingsTable[trainingId] = {};
        }
        trainingsTable[trainingId].score = trainingScores[trainingId];
    });

    Object.keys(isPassedBack).forEach(trainingId => {
        if (trainingsTable[trainingId] === undefined) {
            trainingsTable[trainingId] = {};
        }
        trainingsTable[trainingId].passedBackStatus = isPassedBack[trainingId];
    });

    return trainingsTable;
}

function createTableHeaderElement() {
    const trainingIdHeaderElement = document.createElement("th");
    trainingIdHeaderElement.innerHTML = "training_id";

    const trainingScoreHeaderElement = document.createElement("th");
    trainingScoreHeaderElement.innerHTML = "score";

    const trainingStatusHeaderElement = document.createElement("th");
    trainingStatusHeaderElement.innerHTML = "pass_back_status";

    const tableHeaderElement = document.createElement("tr");

    tableHeaderElement.append(trainingIdHeaderElement, trainingScoreHeaderElement, trainingStatusHeaderElement);

    return tableHeaderElement;
}

function createTableRowElement(trainingInfo, trainingId) {
    const tableRowElement = document.createElement("tr");

    const tableRowIdElement = document.createElement("td");
    tableRowIdElement.innerHTML = `<a href="/trainings/statistics/${trainingId}/">${trainingId}</a>`;

    const tableRowScoreElement = document.createElement("td");
    tableRowScoreElement.innerHTML = trainingInfo.score.toFixed(2) || "none";

    const tableRowStatusElement = document.createElement("td");
    tableRowStatusElement.innerHTML = trainingInfo.passedBackStatus || "none";

    tableRowElement.append(tableRowIdElement, tableRowScoreElement, tableRowStatusElement);

    return tableRowElement;
}

function showRelatedTrainingsTable(trainingScores, isPassedBack) {
    const trainingsTable = getTrainingsTable(trainingScores, isPassedBack);

    const tableElement = document.getElementById("related-trainings-table");

    tableElement.appendChild(createTableHeaderElement());

    Object.keys(trainingsTable).forEach(trainingId => {
        tableElement.appendChild(createTableRowElement(trainingsTable[trainingId], trainingId));
    });
}