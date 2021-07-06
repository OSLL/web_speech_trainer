$(document).ready(function () {
    $("#version-error").hide()
    fetch('/api/version/info/')
        .then(response => response.json())
        .then(responseJson => {

            const versionTable = document.getElementById("version-table");
            if (!responseJson["error"]) {
                const commit_row = document.createElement("tr");
                const commit_name = document.createElement("td");
                commit_name.textContent = "Коммит:";
                commit_row.appendChild(commit_name);
                const commit_value = document.createElement("td");
                commit_value.textContent = responseJson["commit"];
                commit_row.appendChild(commit_value);
                versionTable.appendChild(commit_row);

                const date_row = document.createElement("tr");
                const date_name = document.createElement("td");
                date_name.textContent = "Дата:";
                date_row.appendChild(date_name);
                const date_value = document.createElement("td");
                date_value.textContent = responseJson["date"];
                date_row.appendChild(date_value);
                versionTable.appendChild(date_row);

                const branch_row = document.createElement("tr");
                const branch_name = document.createElement("td");
                branch_name.textContent = "Ветка:";
                branch_row.appendChild(branch_name);
                const branch_value = document.createElement("td");
                branch_value.textContent = responseJson["branch"];
                branch_row.appendChild(branch_value);
                versionTable.appendChild(branch_row);

                const version_row = document.createElement("tr");
                const version_name = document.createElement("td");
                version_name.textContent = "Версия:";
                version_row.appendChild(version_name);
                const version_value = document.createElement("td");
                version_value.textContent = responseJson["version"];
                version_row.appendChild(version_value);
                versionTable.appendChild(version_row);

            } else if (responseJson["data"]) {
                $("#version-error-text").html("Ошибка загрузки файла: " + responseJson["error"]);
                $("#version-error").show();
                const data = document.createElement("tr");
                const pre_data = document.createElement("pre");
                pre_data.textContent = responseJson["data"];
                data.appendChild(pre_data);
                versionTable.appendChild(data);
            } else {
                $("#version-error-text").html("Ошибка загрузки файла: " + responseJson["error"]);
                $("#version-error").show();
            }
        });
});