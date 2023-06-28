function setCriteriaPackDescription(s) {
    parseTableData(s);
}

function parseTableData(s){
    let criteria = s.split("Критерий:").filter(function( obj ) {
        return obj !== '';
    });
    let description = [];
    let grade = [];
    let criterionWeight = [];
    for(let i = 0;i< criteria.length;i++){
        description.push(criteria[i].slice(criteria[i].indexOf('описание:')+"описание: ".length,criteria[i].indexOf('оценка:') - ",\n".length));
        grade.push(criteria[i].slice(criteria[i].indexOf('оценка:')+"оценка: ".length,criteria[i].indexOf('вес критерия =') - ",\n".length));
        criterionWeight.push(criteria[i].slice(criteria[i].indexOf('вес критерия =') + "вес критерия = ".length,criteria[i].length - ".\n".length));
        criteria[i] = criteria[i].slice(0,criteria[i].indexOf(','));
    
        
    } //получили разделённые данные
    const criteriaTable = document.getElementById('criteria-table');
    let criteriaRow = document.createElement("tr");
    let HeadData = ["Критерий","Описание","Оценка","Вес критерия"];
    HeadData.forEach(element => {
        let tableHead = document.createElement("th");
        tableHead.innerText = element;
        criteriaRow.appendChild(tableHead);
    });
    criteriaTable.appendChild(criteriaRow); // заполнили заголовки  
    for(let i = 0;i< criteria.length;i++){ // заполняем таблицу данными
        criteriaRow = document.createElement("tr");
        let criteriaData = document.createElement("td");
        criteriaData.innerText = criteria[i];
        let descriptionData = document.createElement("td");
        descriptionData.innerText = description[i];
        let gradeData = document.createElement("td");
        gradeData.innerText = grade[i];
        let criterionWeightData = document.createElement("td");
        criterionWeightData.innerText = criterionWeight[i];
        criteriaRow.appendChild(criteriaData);
        criteriaRow.appendChild(descriptionData);
        criteriaRow.appendChild(gradeData);
        criteriaRow.appendChild(criterionWeightData);
        criteriaTable.appendChild(criteriaRow);
    }  
} 