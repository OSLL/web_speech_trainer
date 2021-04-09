$(document).ready(function() {
    fetch('/get_login')
        .then(response => response.json())
        .then(responseJson => {
            $("#username").html("Login: " + responseJson['username'])
            $("#trainings").href = `/get_all_trainings?username=${responseJson['username']}&full_name=${responseJson['full_name']}`
        });
})