document.addEventListener("DOMContentLoaded", function() {
    fetch(`/get_current_task_attempt`)
        .then(response => response.json())
        .then(response => {
            let trainingNumber = response["training_number"];
            let attemptCount = response["attempt_count"];
            if (response === {} || trainingNumber === attemptCount) {
                return;
            }
            document.getElementById("training-number").textContent
                = "Номер тренировки: " + response["training_number"] + " / " + response["attempt_count"];
            document.getElementById("current-points").textContent
                = "Баллы за предыдущие тренировки: " + response["current_points"];
            let next_training = document.getElementById("next-training");
            next_training.style.visibility = "visible";
            next_training.style.fontSize = "14pt";
        });
    document.getElementById("next-training-button").onclick = function () {
        window.location.href = `/training_greeting`;
    }
});