$(document).ready(function () {
    $("#header").hide();

    fetch("/api/sessions/info/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] !== "OK") {
                return;
            }

            const username = responseJson["username"];
            const fullName = responseJson["full_name"];

            $("#username").html("Login: " + username);

            $("#trainings").attr(
                "href",
                `/show_all_trainings/?username=${username}&f=username@${username}&f=full_name@${fullName}`
            );

            if ($("#interviews").length) {
                $("#interviews").attr(
                    "href",
                    `/show_all_interviews/?username=${username}&page=0&count=10`
                );
            }

            fetch("/api/task-attempts/")
                .then(response => response.json())
                .then(responseJson => {
                    if (responseJson["message"] !== "OK") {
                        return;
                    }

                    const mode = responseJson["mode"] || "training";

                    if (mode === "interview") {
                        $("#training-number").html(
                            `Интервью: ${responseJson["used_attempts"]} / ${responseJson["attempt_count"]}`
                        );

                        $("#current-points-sum").html("");
                        return;
                    }

                    $("#training-number").html(
                        `Тренировок в текущей попытке: ${responseJson["training_number"]} / ${responseJson["attempt_count"]}`
                    );

                    $("#current-points-sum").html(
                        `Баллы: ${Number(responseJson["current_points_sum"] || 0).toFixed(2)}`
                    );
                });

            $("#header").show();
        });
});