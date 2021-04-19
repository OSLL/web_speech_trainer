function buildCurrentPresentationRow(presentationFileId, presentationJson) {
    const currentPresentationRowElement = document.createElement("tr");

    const presentationPreviewElement = document.createElement("td");
    const presentationPreviewImageElement = document.createElement("img");
    presentationPreviewImageElement.src = `/api/files/presentations/previews/${presentationFileId}/`;
    presentationPreviewImageElement.style.maxWidth = "200px";
    presentationPreviewImageElement.style.maxHeight = "200px";
    presentationPreviewElement.appendChild(presentationPreviewImageElement);
    currentPresentationRowElement.appendChild(presentationPreviewElement);

    const presentationIdElement = document.createElement("td");
    presentationIdElement.textContent = presentationFileId;
    currentPresentationRowElement.appendChild(presentationIdElement);

    const startTrainingElement = document.createElement("td");
    const startTrainingButton = document.createElement("button");
    startTrainingButton.onclick = function() {
        fetch(`/api/trainings/presentations/${presentationFileId}/`, {method: "POST"})
            .then(response => response.json())
            .then(responseJson => {
                if (responseJson["message"] === "OK") {
                    const trainingId = responseJson["training_id"];
                    location.href = `/trainings/${trainingId}/`;
                }
            });
    };
    startTrainingButton.textContent = "Начать тренировку";
    startTrainingElement.appendChild(startTrainingButton);
    currentPresentationRowElement.appendChild(startTrainingElement);

    return currentPresentationRowElement;
}

function buildAllPresentationsTable(presentationsJson) {
    if (presentationsJson["message"] !== "OK") {
        return;
    }
    const allPresentationsTable = document.getElementById("all-presentations-table");
    const titleRow = buildTitleRow(["Превью", "id", ""]);
    allPresentationsTable.appendChild(titleRow);

    Object.keys(presentationsJson["presentations"]).forEach(presentationFileId => {
        const currentPresentationRowElement = buildCurrentPresentationRow(
            presentationFileId,
            presentationsJson["presentations"][presentationFileId]
        );
        allPresentationsTable.appendChild(currentPresentationRowElement);
    });
}

function call_get_all_presentations() {
    fetch("/api/presentations/")
        .then(response => response.json())
        .then(responseJson => buildAllPresentationsTable(responseJson));
}
