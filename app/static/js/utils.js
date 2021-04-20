function buildTitleRow(columns) {
    const titleRowElement = document.createElement("tr");
    columns.forEach(column => {
        const thElement = document.createElement("th");
        thElement.textContent = column;
        titleRowElement.appendChild(thElement);
    });
    return titleRowElement;
}

function strtobool(val, onError= false) {
    try {
        val = val.toLowerCase();
        if (['y', 'yes', 't', 'true', 'on', '1'].includes(val)) {
            return true;
        } else if (['n', 'no', 'f', 'false', 'off', '0'].includes(val)) {
            return false;
        }
    } catch (e) {
        return onError;
    }
}