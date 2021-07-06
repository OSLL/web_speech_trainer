$(document).ready(function () {
    $("#header").hide();
    $("#version-review").hide();
    fetch("/api/sessions/info/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] !== "OK") {
                return;
            }
            $("#username").html("Login: " + responseJson["username"]);
            $("#trainings").attr("href", `/show_all_trainings/?username=${responseJson["username"]}&full_name=${responseJson["full_name"]}`);
            fetch("/api/task-attempts/")
                .then(response => response.json())
                .then(responseJson => {
                    if (responseJson["message"] !== "OK") {
                        return;
                    }
                    $("#training-number").html(`Тренировок в текущей попытке: ${responseJson["training_number"]} / ${responseJson["attempt_count"]}`);
                    $("#current-points-sum").html(`Баллы: ${responseJson["current_points_sum"].toFixed(2)}`);
                });
            $("#header").show();
        });
    fetch("/api/sessions/admin/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] !== "OK") {
                return;
            }
            $("#version-review").show();
        });
});
