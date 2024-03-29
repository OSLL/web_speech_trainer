$(document).ready(function () {
    $("#header").hide();
    fetch("/api/sessions/info/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] !== "OK") {
                return;
            }
            $("#username").html("Login: " + responseJson["username"]);
            $("#trainings").attr("href", `/show_all_trainings/?username=${responseJson["username"]}&f=username@${responseJson["username"]}&f=full_name@${responseJson["full_name"]}`);
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
});
