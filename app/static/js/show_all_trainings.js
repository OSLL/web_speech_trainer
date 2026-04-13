function get_time_string(timestamp){
    let options = {year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit', second: '2-digit'}
    if (!isNaN(timestamp)) {
        let processing_time = new Date(timestamp);
        return processing_time.toLocaleString("ru-RU", options);
    } else {
        return "";
    }
}

function buildCurrentTrainingRow(trainingJson, isAdmin=false) {
    console.log(JSON.stringify(trainingJson))
    const trainingId = trainingJson.training_id;
    const currentTrainingRowElement = document.createElement("tr");

    const trainingIdElement = document.createElement("td");
    const trainingIdLink = document.createElement("a");
    trainingIdLink.href=`/trainings/statistics/${trainingId}/`;
    trainingIdLink.textContent = "..." + String(trainingId).slice(-5);
    trainingIdElement.appendChild(trainingIdLink);
    currentTrainingRowElement.appendChild(trainingIdElement);

    const trainingAttemptIdElement = document.createElement("td");
    if(trainingJson["task_attempt_id"] !== "undefined"){
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

    const trainingCritetiaIdElement = document.createElement("td");
    trainingCritetiaIdElement.textContent = trainingJson["criteria_pack_id"];
    currentTrainingRowElement.appendChild(trainingCritetiaIdElement);

    const taskIdElement = document.createElement("td");
    taskIdElement.textContent = trainingJson["task_id"];
    currentTrainingRowElement.appendChild(taskIdElement);

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
    trainingScoreElement.textContent = trainingJson["score"];
    currentTrainingRowElement.appendChild(trainingScoreElement);

    const presentationFileIdElement = document.createElement("td");
    if (trainingJson["presentation_file_id"] !== "undefined"){
        const presentationFileIdLink = document.createElement("a");
        presentationFileIdLink.textContent = "..." + String(trainingJson["presentation_file_id"]).slice(-5);
        presentationFileIdLink.href = `/api/files/presentations/by-training/${trainingId}/`;
        presentationFileIdLink.target = "_blank";
        presentationFileIdElement.appendChild(presentationFileIdLink);
    }
    currentTrainingRowElement.appendChild(presentationFileIdElement);

    const recordingElement = document.createElement("td");
    if (trainingJson["presentation_record_file_id"] === "None") {
        recordingElement.textContent = "Аудиозапись отсутствует";
    } else {
        const recordingAudio = document.createElement("audio");
        recordingAudio.preload = "none";
        recordingAudio.controls = true;
        recordingAudio.src = `/api/files/presentation-records/${trainingJson["presentation_record_file_id"]}/`;
        recordingElement.appendChild(recordingAudio);
    }
    currentTrainingRowElement.appendChild(recordingElement);

    if (isAdmin) {
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

function buildAllTrainingsTable(trainingsJson) {
    if (trainingsJson["message"] !== "OK") return;

    const allTrainingsTable = document.getElementById("all-trainings-table");
    let titles = [
        "id тренировки",
        "id попытки",
        "Логин",
        "Имя",
        "Набор критериев",
        "Задание",
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

    fetch('/api/sessions/admin')
    .then(response => response.json())
    .then(responseJson => {
        const isAdmin = responseJson.admin;
        const arrayTrainings = trainingsJson.trainings; // Array of train from FETCH
        
        if (isAdmin) {
            titles.push('Запустить перепроверку');
        }

        const titleRow = buildTitleRow(titles);
        allTrainingsTable.appendChild(titleRow);
        
        Object.keys(arrayTrainings).forEach(index => {
            const currentTrainingRowElement = buildCurrentTrainingRow(
                arrayTrainings[index], 
                isAdmin
            );
            
            allTrainingsTable.appendChild(currentTrainingRowElement);
        });
        initVisibilityCheckboxes(allTrainingsTable)
    })
    .catch(err => console.log(err));
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

function call_get_all_trainings({filters, page = 0, count}) {
    const query = new URLSearchParams({
        filters,
        count
    });

    query.append('page', String(page));

    return fetch(`/api/trainings?${query.toString()}`)
        .then(response => response.json())
        .then(responseJson => buildAllTrainingsTable(responseJson));
}

function setColumnVisibility(table, columnIndex, visible) {
    const cells = table.querySelectorAll(`td:nth-child(${columnIndex}), th:nth-child(${columnIndex})`);
    cells.forEach(cell => {
        cell.style.display = visible ? '' : 'none';
    });
}

function getCurrentVisibility(table) {
    const firstRow = table.querySelector('tr');
    if (!firstRow) return [];
    const colCount = firstRow.cells.length;
    const visibility = [];
    for (let i = 1; i <= colCount; i++) {
        const anyCell = table.querySelector(`td:nth-child(${i}), th:nth-child(${i})`);
        visibility.push(anyCell ? anyCell.style.display !== 'none' : true);
    }
    return visibility;
}

function applySavedVisibility(table, hiddenIndices) {
    const colCount = table.querySelector('tr')?.cells.length || 0;
    for (let i = 1; i <= colCount; i++) {
        const shouldBeHidden = hiddenIndices.includes(i);
        setColumnVisibility(table, i, !shouldBeHidden);
    }
}

function saveVisibility(table) {
    const visibility = getCurrentVisibility(table);
    const hiddenIndices = visibility.reduce((acc, isVisible, idx) => {
        if (!isVisible) acc.push(idx + 1); // индексы с 1
        return acc;
    }, []);
    localStorage.setItem('hidden_columns', JSON.stringify(hiddenIndices));
}

function createControlPanel(table) {
    const headerRow = table.querySelector('tr');
    const colCount = headerRow ? headerRow.cells.length : (table.querySelector('tr')?.cells.length || 0);
    console.log(colCount)
    const container = document.createElement('div');
    container.className = 'column-control-panel';

    const title = document.createElement('span');
    title.textContent = 'Видимость столбцов: ';
    title.style.fontWeight = 'bold';
    container.appendChild(title);

    const checkboxes = [];

    for (let i = 1; i <= colCount; i++) {
        let labelText = `Колонка ${i}`;
        if (headerRow && headerRow.cells[i - 1]) {
            labelText = headerRow.cells[i - 1].textContent.trim() || labelText;
        }

        const label = document.createElement('label');
        label.style.marginLeft = '10px';
        label.style.cursor = 'pointer';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = true;
        cb.dataset.columnIndex = i;

        cb.addEventListener('change', (function (idx, checkbox) {
            return function () {
                setColumnVisibility(table, idx, checkbox.checked);
                saveVisibility(table);
            };
        })(i, cb));

        label.appendChild(cb);
        label.appendChild(document.createTextNode(' ' + labelText));
        container.appendChild(label);
        checkboxes.push(cb);
    }

    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Сбросить';
    resetBtn.style.marginLeft = '20px';
    resetBtn.addEventListener('click', () => {
        localStorage.removeItem('hidden_columns');
        for (let i = 1; i <= colCount; i++) {
            setColumnVisibility(table, i, true);
            if (checkboxes[i - 1]) checkboxes[i - 1].checked = true;
        }
    });
    container.appendChild(resetBtn);

    const hidePanelBtn = document.createElement('button');
    hidePanelBtn.textContent = 'Скрыть панель';
    hidePanelBtn.style.marginLeft = '10px';
    hidePanelBtn.addEventListener('click', () => {
        container.style.display = 'none';
        showPanelBtn.style.display = 'inline-block';
        localStorage.removeItem('visibility_panel_show');
    });
    container.appendChild(hidePanelBtn);

    const showPanelBtn = document.createElement('button');
    showPanelBtn.textContent = 'Показать настройку видимости столбцов';
    showPanelBtn.addEventListener('click', () => {
        container.style.display = '';
        showPanelBtn.style.display = 'none';
        localStorage.setItem('visibility_panel_show', 'true');
    });
    document.body.appendChild(showPanelBtn);

    table.parentNode.insertBefore(container, table);
    container.parentNode.insertBefore(showPanelBtn, container);

    var returnable = new Object();
    returnable.panelContainer = container;
    returnable.showPanelBtn = showPanelBtn;
    returnable.checkboxes = checkboxes;
    returnable.colCount = colCount;

    return returnable;
}

function initVisibilityCheckboxes(table) {
    const panelObjects = createControlPanel(table);
    const checkboxes = panelObjects.checkboxes;
    const saved = localStorage.getItem('hidden_columns');
    let hiddenIndices = [];
    if (saved) {
        try {
            hiddenIndices = JSON.parse(saved);
            if (!Array.isArray(hiddenIndices)) hiddenIndices = [];
        } catch (e) { hiddenIndices = []; }
    }

    for (let i = 1; i <= panelObjects.colCount; i++) {
        const hidden = hiddenIndices.includes(i);
        setColumnVisibility(table, i, !hidden);
        if (checkboxes[i - 1]) checkboxes[i - 1].checked = !hidden;
    }

    if (localStorage.getItem('visibility_panel_show') === 'true') {
        panelObjects.panelContainer.style.display = '';
        panelObjects.showPanelBtn.style.display = 'none';
    } else {
        panelObjects.panelContainer.style.display = 'none';
        panelObjects.showPanelBtn.style.display = 'inline-block';
    }

}
