const tableColomnHeaders = [
    "№", "training_id", "start_timestamp", "training_status", "pass_back_status",  "score"
];

function get_time_string(timestampStr){
    const timestamp = Date.parse(timestampStr);

    options = { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }
    if (!isNaN(timestamp)) {
        processing_time = new Date(timestamp);
        return processing_time.toLocaleString("ru-RU", options);
    } else {
        return "";
    }
}

function createTableHeaderElement() {
    const tableHeaderElement = document.createElement("tr");

    tableColomnHeaders.forEach(colomnHeader => {
        const tableColomnHeaderElement = document.createElement("th");
        tableColomnHeaderElement.innerHTML = colomnHeader;

        tableHeaderElement.appendChild(tableColomnHeaderElement);
    });

    return tableHeaderElement;
}

function createTableRowElement() {
    const tableRowElement = document.createElement("tr");

    const tableRow = {};

    tableColomnHeaders.forEach(columnHeader => {
        const tableCellElement = document.createElement("td");

        tableRow[columnHeader] = tableCellElement;
        tableRowElement.appendChild(tableCellElement);
    });

    return [tableRowElement, tableRow];
}

function TableRowFiller() {
    let pos = 1;

    function fillTableRow(tableRow, training) {
        tableRow["№"].innerHTML = pos++;
        tableRow["training_id"].innerHTML = `<a href="/trainings/statistics/${training.id}/">${training.id}</a>`;
        tableRow["start_timestamp"].innerHTML = get_time_string(training.training_start_timestamp);
        tableRow["score"].innerHTML = training.score ? training.score.toFixed(2) : "none";
        tableRow["training_status"].innerHTML = training.training_status;
        tableRow["pass_back_status"].innerHTML = training.passedBackStatus || "none";
    }

    return fillTableRow;
}

function getSortedTrainingsList(trainings) {
    const trainingsList = [];

    Object.keys(trainings).forEach(trainingId => {
        const training = trainings[trainingId];
        training["id"] = trainingId;

        trainingsList.push(training);
    });

    trainingsList.sort((a, b) => {
        return Date.parse(a) - Date.parse(b);
    });

    return trainingsList;
}

function showRelatedTrainingsTable(trainings) {
    const tableElement = document.getElementById("related-trainings-table");

    tableElement.appendChild(createTableHeaderElement());

    const trainingsList = getSortedTrainingsList(trainings);

    const fillTableRow = TableRowFiller();

    trainingsList.forEach(training => {
        const [tableRowElement, tableRow] = createTableRowElement();

        fillTableRow(tableRow, training);

        tableElement.appendChild(tableRowElement);
    });
}