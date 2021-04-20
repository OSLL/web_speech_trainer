$(document).ready(function() {
    fetch('/get_login')
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson['username'] != '') {
                $("#header").show();
                $("#username").html("Login: " + responseJson['username']);
                $("#trainings").href = `/api/trainings/?username=${responseJson['username']}&full_name=${responseJson['full_name']}`;
            } else {
                $("#header").hide();
            }
        });
})