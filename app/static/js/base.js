document.addEventListener("DOMContentLoaded", function() {
    fetch("/api/sessions/user-agent/")
        .then(response => response.json())
        .then(responseJson => {
            if (responseJson["message"] === "OK" && responseJson["outdated"] === true) {
                const alertElement = document.createElement("div");
                alertElement.classList.add("alert");
                alertElement.classList.add("alert-warning");
                alertElement.setAttribute("role", "alert");
                alertElement.textContent = `Поддерживаемые ОС: ${responseJson["supportedPlatforms"].join(", ")}, 
                    поддерживаемые браузеры и версии: ${JSON.stringify(responseJson["supportedBrowsers"])
                        .split("\",\"").join("\", \"")}. 
                    Ваша ОС: ${responseJson["platform"]}, 
                    Ваш браузер: ${responseJson["browser"]}, версия: ${responseJson["version"]}.`;
                document.body.insertBefore(alertElement, document.body.firstChild);
            }
        });
});
