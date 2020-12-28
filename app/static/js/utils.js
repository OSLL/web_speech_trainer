function buildTitleRow(columns) {
    const titleRowElement = document.createElement('tr');
    columns.forEach(column => {
        const thElement = document.createElement('th');
        thElement.textContent = column;
        titleRowElement.appendChild(thElement);
    });
    return titleRowElement;
}
