function setCriteriaPackDescription(s) {
   // document.getElementById('criteria-pack-description').innerText = `${s}`;
   const criteriaTable = document.getElementById("criteria-table");
   let criteriaRow = document.createElement("tr");
   let HeadData = ["Критерий","Описание","Оценка","Вес критерия"];
   HeadData.forEach(element =>{
    let tableHead = document.createElement("th");
    tableHead.innerText = element;
    criteriaRow.appendChild(tableHead);
   });
   criteriaTable.appendChild(criteriaRow);
   for(let i = 0;i < s["Критерии"].length;i++){
    criteriaRow = document.createElement("tr");
    let criteriaData = document.createElement("td");
    criteriaData.innerText = s["Критерии"][i]["Критерий"];
    let descriptionData = document.createElement("td");
    descriptionData.innerText = s["Критерии"][i]["Описание"];  
    let gradeData = document.createElement("td");
    gradeData.innerText = s["Критерии"][i]["Оценка"]; 
    let criterionWeightData = document.createElement("td");
    criterionWeightData.innerText = s["Критерии"][i]["Вес"];
    criteriaRow.appendChild(criteriaData);
    criteriaRow.appendChild(descriptionData);
    criteriaRow.appendChild(gradeData);
    criteriaRow.appendChild(criterionWeightData);
    criteriaTable.appendChild(criteriaRow);
   }
}