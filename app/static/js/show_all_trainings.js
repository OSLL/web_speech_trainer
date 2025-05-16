function get_time_string(timestamp){
    options = { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }
    if (!isNaN(timestamp)) {
        processing_time = new Date(timestamp);
        return processing_time.toLocaleString("ru-RU", options);
    } else {
        return "";
    }
}

function buildCurrentTrainingRow(trainingId, trainingJson, is_Admin=false) {

    const currentTrainingRowElement = document.createElement("tr");

    const trainingIdElement = document.createElement("td");
    const trainingIdLink = document.createElement("a");
    trainingIdLink.href=`/trainings/statistics/${trainingId}/`;
    trainingIdLink.textContent = "..." + String(trainingId).slice(-5);
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

    const trainingAttemptIdElement = document.createElement("td");
    if(trainingJson["task_attempt_id"] !== "undefined" && trainingJson["message"] === "OK"){
        const trainingAttemptIdLink = document.createElement("a");
        trainingAttemptIdLink.href=`/task_attempts/${trainingJson["task_attempt_id"]}`;
        trainingAttemptIdLink.textContent = `...${(trainingJson["task_attempt_id"]).slice(-5)}`;
        trainingAttemptIdElement.appendChild(trainingAttemptIdLink);
    }
    currentTrainingRowElement.appendChild(trainingAttemptIdElement);

    const trainingUsernameElement = document.createElement("td");
    const trainingUsernameLink = document.createElement("a");
    trainingUsernameLink.href = `/show_all_trainings/?username=${trainingJson["username"]}&f=username${KEY_VALUE_DELIMITER}${trainingJson["username"]}&f=full_name${KEY_VALUE_DELIMITER}${trainingJson["full_name"]}`;
    trainingUsernameLink.textContent = trainingJson["username"];
    trainingUsernameElement.appendChild(trainingUsernameLink);
    currentTrainingRowElement.appendChild(trainingUsernameElement);

    const trainingFullNameElement = document.createElement("td");
    trainingFullNameElement.textContent = trainingJson["full_name"];
    currentTrainingRowElement.appendChild(trainingFullNameElement);

    const presentationRecordDurationElement = document.createElement("td");
    presentationRecordDurationElement.textContent = trainingJson["presentation_record_duration"];
    currentTrainingRowElement.appendChild(presentationRecordDurationElement);
   
    const trainingStartTimestampElement = document.createElement("td");
    start_timestap = Date.parse(trainingJson["training_start_timestamp"]);
    trainingStartTimestampElement.textContent = get_time_string(start_timestap);
    currentTrainingRowElement.appendChild(trainingStartTimestampElement);

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
        recordingAudio.preload = "none";
        recordingAudio.controls = true;
        recordingAudio.src = `/api/files/presentation-records/${trainingJson["presentation_record_file_id"]}/`;
        recordingElement.appendChild(recordingAudio);
    }
    currentTrainingRowElement.appendChild(recordingElement);

    if (is_Admin) {
        const recheckingElement = document.createElement("td");
        const button = document.createElement("input")
        button.type = "button"
        button.value = "Запустить перепроверку"
        button.name = `${trainingId}`        
        button.onclick = function () { recheck(this.name); };
        recheckingElement.appendChild(button);
        currentTrainingRowElement.appendChild(recheckingElement);
    }
    return currentTrainingRowElement;
}

function recheck(trainingId){
    console.log(`Start recheck for ${trainingId}`)
    fetch(`/api/trainings/${trainingId}/`, {method: "POST"})
    .then(response => response.json())
    .then(innerResponseJson => {
        if (innerResponseJson["message"] === "OK") {
            window.open(`/trainings/statistics/${trainingId}/`);
            //location.href = `/trainings/statistics/${trainingId}/`;
        }
    });
}

function buildAllTrainingsTable(trainingsJson, is_Admin=false) {
    if (trainingsJson["message"] !== "OK") return;

    const allTrainingsTable = document.getElementById("all-trainings-table");
    let titles = [
        "id тренировки",
        "id попытки",
        "Логин",
        "Имя",
        "Длительность аудиозаписи",
        "Начало тренировки",
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
    if (is_Admin) {titles.push('Запустить перепроверку')}
    const titleRow = buildTitleRow(titles);
    allTrainingsTable.appendChild(titleRow);

    const arrayTrainings = trainingsJson.trainings; // Array of train from FETCH

    Object.keys(arrayTrainings).forEach(trainingId => {
        const currentTrainingRowElement = buildCurrentTrainingRow(trainingId, arrayTrainings[trainingId], is_Admin);
        allTrainingsTable.appendChild(currentTrainingRowElement);
    });
}

const REF_PAGE_COUNT = document.getElementById('ref-page-count');
const REF_BUTTON_TO_START = document.getElementById('btn-to-start');
const REF_BUTTON_TO_END   = document.getElementById('btn-to-end');

let rowsPerPage = REF_PAGE_COUNT.value;
let currentPage = 0;
let pageTotal = 0;
let rowsTotal = 0;

function initPagination(pageString, countString) {
    currentPage = parseInt(pageString);
    rowsPerPage = parseInt(countString);

    changeURLByParam("page", currentPage.toString())
    changeURLByParam("count", rowsPerPage.toString())

    let found = false
    for (const element of REF_PAGE_COUNT.getElementsByTagName('option')) {
        if (rowsPerPage === parseInt(element.value)) {
            found = true
            break
        }
    }

    if (!found) {
        rowsPerPage = REF_PAGE_COUNT.value
    }

    REF_PAGE_COUNT.value = rowsPerPage
}

function setPaginationInfo(){
    $("#pagination-info").text(`Страница ${currentPage + 1} из ${pageTotal}`);
}

function blockButtons(){
    const isEnd = currentPage === pageTotal - 1;
    const isStart = currentPage === 0;

    $("#btn-left").prop('disabled', isStart);
    $("#btn-right").prop('disabled', isEnd);

    REF_BUTTON_TO_END.toggleAttribute('disabled', isEnd);
    REF_BUTTON_TO_START.toggleAttribute('disabled', isStart)
}

/**
 * @description Remove tr and call call_get_all_trainings
 * */
function changeRows(){
    /**
     * @description Searching tr of tables and removing them.
     */
    const arrayRow = [...document.querySelectorAll("#all-trainings-table tr")]
    arrayRow.forEach(refElement => refElement.parentElement.removeChild(refElement))

    call_get_all_trainings({
        filters: getFiltersJSON(),
        page: currentPage,
        count: rowsPerPage
    })
    .catch(err => {
        console.error(err);
    })
}

function updatePagination(pageDirection = currentPage * -1, updatePagePointer = true){
    if (updatePagePointer)
        currentPage += pageDirection;
    
    if (currentPage >= pageTotal){
        currentPage = 0
        changeURLByParam("page", currentPage.toString())
    }
    
    changeRows();
    blockButtons();
    setPaginationInfo();
}

$("#btn-left").click(function() {
    updatePagination(-1);
    changeURLByParam("page", currentPage.toString())
});

$("#btn-right").click(function() {
    updatePagination(1);
    changeURLByParam("page", currentPage.toString())
});


async function updateCountPage() {
    const query = new URLSearchParams({
        filters: getFiltersJSON(),
        count: rowsPerPage
    });
    pageTotal = await fetch(`/api/trainings/count-page?${query.toString()}`)
    .then(a => a.json())
    .then(data => data.count)
    REF_BUTTON_TO_END.innerText = pageTotal;
}

function call_get_all_trainings({filters, admin=false, page = 0, count}) {
    const query = new URLSearchParams({
        filters,
        count
    });

    query.append('page', String(page));

    return fetch(`/api/trainings?${query.toString()}`)
        .then(response => response.json())
        .then(responseJson => buildAllTrainingsTable(responseJson, admin));
}
