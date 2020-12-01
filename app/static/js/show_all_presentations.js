function buildCurrentPresentationRow(presentationFileId, presentationJson) {
    const currentPresentationRowElement = document.createElement('tr');

    const presentationPreviewElement = document.createElement('td');
    const presentationPreviewImageElement = document.createElement('img');
    presentationPreviewImageElement.src = `/get_presentation_preview?presentationFileId=${presentationFileId}`;
    presentationPreviewImageElement.style.maxWidth = "200px";
    presentationPreviewImageElement.style.maxHeight = "200px";
    presentationPreviewElement.appendChild(presentationPreviewImageElement);
    currentPresentationRowElement.appendChild(presentationPreviewElement);

    const presentationIdElement = document.createElement('td');
    presentationIdElement.textContent = presentationFileId;
    currentPresentationRowElement.appendChild(presentationIdElement);


    const startTrainingElement = document.createElement('td');
    const startTrainingLink = document.createElement('a');
    startTrainingLink.href=`/training/${presentationFileId}/`;
    startTrainingLink.text = 'Начать тренировку';
    startTrainingElement.appendChild(startTrainingLink);
    currentPresentationRowElement.appendChild(startTrainingElement);

    return currentPresentationRowElement;
}

function buildAllPresentationsTable(presentationsJson) {
    const allPresentationsTable = document.getElementById('all-presentations-table');
    const titleRow = buildTitleRow(['Превью', 'id', '']);
    allPresentationsTable.appendChild(titleRow);

    Object.keys(presentationsJson).forEach(presentationFileId => {
        const currentPresentationRowElement = buildCurrentPresentationRow(
            presentationFileId,
            presentationsJson[presentationFileId]
        );
        allPresentationsTable.appendChild(currentPresentationRowElement);
    });
}

function call_get_all_presentations() {
    fetch('/get_all_presentations')
        .then(response => response.json())
        .then(responseJson => buildAllPresentationsTable(responseJson));
}
