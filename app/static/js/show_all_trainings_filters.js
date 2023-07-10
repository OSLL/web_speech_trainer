const filterType = {
    TEXT: {
        name: "text",
        filterCreationMethod: createTextFilter,
        hasMultipleValues: false
    },
    RANGE: {
        name: "range",
        filterCreationMethod: createRangeFilter,
        hasMultipleValues: true
    },
    DATE: {
        name: "date",
        filterCreationMethod: createDateFilter,
        hasMultipleValues: true
    },
    CHOICE: {
        name: "choice",
        filterCreationMethod: createChoiceFilter,
        hasMultipleValues: true
    },
}

const LINK_PARAM_NAME = "f"
const PARAM_DELIMITER = "~";
const FILTER_DELIMITER = "&";
const KEY_VALUE_DELIMITER = "@";


function parseFiltersString(raw_filters) {
    let filters = {};

    raw_filters = raw_filters.split(FILTER_DELIMITER);

    for (const raw_filter of raw_filters) {

        let decodedRawFilter = decodeURIComponent(raw_filter);
        if (!decodedRawFilter.includes(KEY_VALUE_DELIMITER) || decodedRawFilter.split(KEY_VALUE_DELIMITER).length !== 2)
            continue;

        let split_filter = decodedRawFilter.split(KEY_VALUE_DELIMITER);

        if (split_filter[0].length === 0 || split_filter[1].length === 0)
            continue;

        filters[split_filter[0]] = split_filter[1]
    }

    return filters;
}

function getFiltersJSON() {
    let json = {};

    for (const [key, value] of Object.entries(originalFilters)) {
        json[key] = value.split(PARAM_DELIMITER);
    }

    return JSON.stringify(json);
}


function isInRecordDurationForm(str) {
    let regex = /^\d\d:\d\d$/i;
    return regex.test(str);
}

function recordDurationStringToSeconds(durationString) {
    let splitString = durationString.split(":");

    let minutes = parseInt(splitString[0]);
    let seconds = parseInt(splitString[1]);

    return minutes * 60 + seconds;
}

function recordDurationToString(duration) {
    let minutesString = Math.floor(duration / 60).toString();
    let secondsString = (duration % 60).toString();

    if (minutesString.length === 1) minutesString = "0" + minutesString;
    if (secondsString.length === 1) secondsString = "0" + secondsString;

    return minutesString + ":" + secondsString;
}

function isFloat(str) {
    return !isNaN(parseFloat(str))
}


function getFiltersCountText() {
    let count = Object.keys(originalFilters).length;

    let text = 'Фильтры не применены';

    if (count !== 0) {
        text = getValuesCountText(count, "Фильтр применен", "Фильтра применено", "Фильтров применено");
    }

    return text;
}

function getValuesCountText(count, oneElementText, twoToFourElementText, elseText) {
    let text = ""

    if (count % 100 !== 11 && count % 10 === 1) {
        text = oneElementText
    } else if (count % 100 !== 12 && count % 10 === 2 || count % 100 !== 13 && count % 10 === 3 || count % 100 !== 14 && count % 10 === 4) {
        text = twoToFourElementText
    } else {
        text = elseText
    }

    return count + " " + text;
}

/**
 * Disables or enables apply button based on state
 * @param hasChanged if currentFilters has changed and doesn't copy originalFilters
 */
function setFiltersChanged(hasChanged) {
    applyFiltersButton.button("option", "disabled", !hasChanged);
}

/**
 * Checks if originalFilters and currentFilters differ somehow and sets availability of apply button based on answer
 */
function checkIfFiltersChanged() {

    if (Object.keys(originalFilters).length !== Object.keys(currentFilters).length) {
        setFiltersChanged(true)
        return
    }

    if (Object.keys(originalFilters).length === 0) {
        setFiltersChanged(false);
        return;
    }

    for (const [key, value] of Object.entries(originalFilters)) {
        if (!currentFilters.hasOwnProperty(key)) {
            setFiltersChanged(true)
            return
        }
        if (filtersData[key].type.hasMultipleValues) {
            let sortedValue = value.split(PARAM_DELIMITER).sort()
            let currentValue = currentFilters[key].split(PARAM_DELIMITER).sort()

            if (sortedValue.length !== currentValue.length) {
                setFiltersChanged(true)
                return
            }
            for (let i = 0; i < sortedValue.length; i++) {
                if (sortedValue[i] !== currentValue[i]) {
                    setFiltersChanged(true)
                    return
                }
            }
        } else {
            if (value !== currentFilters[key]) {
                setFiltersChanged(true)
                return
            }
        }
    }

    setFiltersChanged(false)


}

/**
 * Copies all elements from originalFilters to currentFilters
 */
function restoreCurrentFiltersFromOrig() {
    currentFilters = {}
    for (const [key, value] of Object.entries(originalFilters)) {
        currentFilters[key] = value
    }
}

/**
 * Copies all elements from currentFilters to originalFilters
 */
function copyCurrentFiltersToOrig() {
    originalFilters = {}
    for (const [key, value] of Object.entries(currentFilters)) {
        originalFilters[key] = value
    }
}


/**
 * Creates base for any filter interface: a row that consists of name, input and remove button
 * @param filterCode Code of filter to implement interface for
 * @param inputElements Elements to add to input part of interface
 */
function createFilterBase(filterCode, ...inputElements) {
    let contentWrapper = $("#filters-list .content-wrapper");

    let row = $("<div></div>").attr("id", filterCode + "-filter").addClass("filter-row").addClass(filtersData[filterCode].type.name + "-type");

    let nameWrapper = $("<div></div>").addClass("filter-name");
    let nameDiv = $("<div></div>")
        .attr("class", "tooltip-text")
        .attr("title", filtersData[filterCode].description)
        .text(filtersData[filterCode].name)
        .tooltip();
    nameWrapper.append(nameDiv)

    let inputPartDiv = $("<div></div>").addClass("filter-input");
    inputPartDiv.append(inputElements);

    let removeBtnDiv = $("<div></div>").addClass("filter-remove");
    let removeBtn = $("<button></button>").attr("class", "remove-btn").on("click", (event) => {
        delete currentFilters[filterCode]
        checkIfFiltersChanged()

        if (Object.keys(currentFilters).length === 0) {
            $("#filters-list .content-wrapper").addClass("hidden");
            $("#no-filters-text").removeClass("hidden");
        } else {
            $("#filters-list .content-wrapper").removeClass("hidden");
            $("#no-filters-text").addClass("hidden");
        }

        $("#filters-to-choose-select #" + filterCode + "-option").attr("disabled", false);

        let selectmenu = $("#filters-to-choose-select");
        selectmenu.selectmenu("enable")
        selectmenu.selectmenu("refresh");

        row.remove()
    });

    removeBtn.text("X");
    removeBtnDiv.append(removeBtn);

    removeBtn.button().removeClass("ui-button").addClass("button_action");

    row.append(nameWrapper, inputPartDiv, removeBtnDiv);

    contentWrapper.append(row);

}

/**
 * Creates text filter. It includes creation of interface and data in currentFilters
 * @param filterCode Code of filter to control
 * @param initialValue A string value to insert to input field
 */
function createTextFilter(filterCode, initialValue = "") {

    if (filtersData[filterCode].type !== filterType.TEXT) {
        console.error("Filter " + filterCode + " tried to create text type filter field!");
        return;
    }

    if (initialValue === "") {
        currentFilters[filterCode] = "";
        checkIfFiltersChanged()
    }

    let input = $("<input>")
        .attr("type", "text")
        .attr("placeholder", filtersData[filterCode].placeholder)
        .attr("id", filterCode + "-filter-input")
        .on("input", () => {
            currentFilters[filterCode] = input.val().trim()
            checkIfFiltersChanged()
        });
    input.val(initialValue);


    createFilterBase(filterCode, input);
}

/**
 * Creates range filter. It includes creation of interface and data in currentFilters
 * @param filterCode Code of filter to control
 * @param initialValues A string with 2 values in format "mm:ss" split by PARAM_DELIMITER. First - start of range, Second - it's end.
 */
function createRangeFilter(filterCode, initialValues = "") {

    if (filtersData[filterCode].type !== filterType.RANGE) {
        console.error("Filter " + filterCode + " tried to create range type filter field!");
        return;
    }

    if (initialValues.split(PARAM_DELIMITER).length > 2) {
        console.error("Filter " + filterCode + " received too many params!");
        return;
    } else if (initialValues.split(PARAM_DELIMITER).length === 2) {
        let splitInitialValues = initialValues.split(PARAM_DELIMITER);

        initialValues = []
        initialValues.push(filtersData[filterCode].toValueMethod(splitInitialValues[0]));
        initialValues.push(filtersData[filterCode].toValueMethod(splitInitialValues[1]));
    } else {
        initialValues = []
        initialValues.push(filtersData[filterCode].range_start);
        initialValues.push(filtersData[filterCode].range_end);

        currentFilters[filterCode] = [filtersData[filterCode].toStringMethod(initialValues[0]), filtersData[filterCode].toStringMethod(initialValues[1])].join(PARAM_DELIMITER);
        checkIfFiltersChanged()
    }

    let startInput = $("<input>").addClass("start-input")
        .attr("type", "text")
        .attr("id", filterCode + "-start-filter-input")
        .val(filtersData[filterCode].toStringMethod(initialValues[0]))
        .on("input", () => {

            let possibleDuration = startInput.val();

            if (filtersData[filterCode].checkTextFormat(possibleDuration)) {
                let durationStart = filtersData[filterCode].toValueMethod(possibleDuration);
                let splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);

                if (durationStart <= filtersData[filterCode].toValueMethod(splitCurrentValues[1])) {
                    rangeInput.slider('values', 0, durationStart)

                    splitCurrentValues[0] = possibleDuration
                    currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);

                    checkIfFiltersChanged()
                }
            }
        });

    let endInput = $("<input>").addClass("end-input")
        .attr("type", "text")
        .attr("id", filterCode + "-end-filter-input")
        .val(filtersData[filterCode].toStringMethod(initialValues[1]))
        .on("input", () => {

            let possibleDuration = endInput.val();
            if (filtersData[filterCode].checkTextFormat(possibleDuration)) {
                let durationEnd = filtersData[filterCode].toValueMethod(possibleDuration);
                let splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);

                if (durationEnd >= filtersData[filterCode].toValueMethod(splitCurrentValues[0])) {
                    rangeInput.slider('values', 1, durationEnd);

                    splitCurrentValues[1] = possibleDuration;
                    currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);

                    checkIfFiltersChanged();
                }
            }
        });

    let rangeInput = $("<div></div>").addClass("range-input")
        .slider({
            range: true,
            min: filtersData[filterCode].range_start,
            max: filtersData[filterCode].range_end,
            step: filtersData[filterCode].step,
            values: initialValues,
            slide: (event, ui) => {
                startInput.val(filtersData[filterCode].toStringMethod(ui.values[0]))
                endInput.val(filtersData[filterCode].toStringMethod(ui.values[1]))

                let splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);

                splitCurrentValues[0] = filtersData[filterCode].toStringMethod(ui.values[0]);
                splitCurrentValues[1] = filtersData[filterCode].toStringMethod(ui.values[1]);
                currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);

                checkIfFiltersChanged();
            }
        });


    createFilterBase(filterCode, startInput, rangeInput, endInput);
}

/**
 * Creates date filter with only Year - Month - Date (No time). It behaves as range filter but with date, except that start date set to the beggining of day and end date is set to the end of day.
 * It includes creation of interface and data in currentFilters
 * @param filterCode Code of filter to control
 * @param initialValues A string with 2 string values of dates in UTC format split by PARAM_DELIMITER. First - start date, Second - it's end date
 */
function createDateFilter(filterCode, initialValues = "") {
    if (filtersData[filterCode].type !== filterType.DATE) {
        console.error("Filter " + filterCode + " tried to create date type filter field!");
        return;
    }

    if (initialValues === "") {
        initialValues = [];
        initialValues[0] = new Date();

        initialValues[1] = new Date();
        initialValues[1].setHours(23, 59, 59, 999);

        currentFilters[filterCode] = [initialValues[0].toISOString(), initialValues[1].toISOString()].join(PARAM_DELIMITER);
        checkIfFiltersChanged()
    } else if (initialValues.split(PARAM_DELIMITER).length === 2) {
        let splitInitialValues = initialValues.split(PARAM_DELIMITER);
        initialValues = []
        initialValues[0] = new Date(Date.parse(splitInitialValues[0]));
        initialValues[1] = new Date(Date.parse(splitInitialValues[1]));
    } else {
        console.error("Filter " + filterCode + " received wrong amount of params!");
        return;
    }


    let fromDiv = $("<div></div>").attr("class", "date-from");

    let fromLabel = $("<label></label>").text("От: ").attr("for", filterCode + "-from-datepicker");
    let fromInput = $("<input>").attr("type", "text").attr("id", filterCode + "-from-datepicker").attr("readonly", "true").datepicker({
        changeMonth: true,
        changeYear: true
    }).on("change", () => {
        toInput.datepicker("option", "minDate", fromInput.datepicker("getDate"))

        let splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);
        splitCurrentValues[0] = fromInput.datepicker("getDate").toISOString();
        currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);
        checkIfFiltersChanged();
    });
    fromInput.datepicker("setDate", initialValues[0]);

    fromDiv.append(fromLabel, fromInput);


    let toDiv = $("<div></div>").attr("class", "date-to");

    let toLabel = $("<label></label>").text("До: ").attr("for", filterCode + "-to-datepicker");
    let toInput = $("<input>").attr("type", "text").attr("id", filterCode + "-to-datepicker").attr("readonly", "true").datepicker({
        changeMonth: true,
        changeYear: true
    }).on("change", () => {
        fromInput.datepicker("option", "maxDate", toInput.datepicker("getDate"))

        let date = new Date(toInput.datepicker("getDate"));
        date.setHours(23, 59, 59, 999);

        let splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);

        splitCurrentValues[1] = date.toISOString();
        currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);
        checkIfFiltersChanged();
    });
    toInput.datepicker("setDate", initialValues[1])

    toDiv.append(toLabel, toInput);


    createFilterBase(filterCode, fromDiv, toDiv);


}

/**
 * Creates choice filter. It includes creation of interface and data in currentFilters
 * @param filterCode Code of filter to control
 * @param initialValues A string with already selected values split by PARAM_DELIMITER
 */
function createChoiceFilter(filterCode, initialValues = "") {
    if (filtersData[filterCode].type !== filterType.CHOICE) {
        console.error("Filter " + filterCode + " tried to create choice type filter field!");
        return;
    }

    if (initialValues !== "") {
        let splitInitialValues = initialValues.split(PARAM_DELIMITER);

        for (const initialValue of splitInitialValues) {
            let found = false;
            for (const value of filtersData[filterCode].values) {
                if (value === initialValue) {
                    found = true;
                    break
                }
            }

            if (!found) {
                console.error("Initial value \"" + initialValue + "\" for filter " + filterCode + " is not in the allowed list of values.");
                return;
            }
        }

        initialValues = splitInitialValues;

    } else {
        currentFilters[filterCode] = ""
        checkIfFiltersChanged()
    }

    let accordionDiv = $("<div></div>").attr("class", "accordion " + filterCode + "-accordion");

    let titleH3 = $("<h3></h3>").attr("class", "choice-accordion-title-h3");
    let titleH3Div = $("<div></div>").text(getValuesCountText(initialValues.length, "Значение выбрано", "Значения выбрано", "Значений выбрано"));
    titleH3.append(titleH3Div);

    let div = $("<div></div>");
    let groupDiv = $("<div></div>").attr("class", "group");

    for (const value of filtersData[filterCode].values) {
        let id = filterCode + "-" + value;

        let isCheckedInitially = $.inArray(value, initialValues) !== -1;

        let label = $("<label></label>").attr("for", id).text(value);
        let input = $("<input>")
            .attr("type", "checkbox")
            .prop("checked", isCheckedInitially)
            .attr("name", id)
            .attr("id", id)
            .on("click", (e) => {
                e.stopPropagation()
            })
            .on("change", () => {
                let splitCurrentValues = []

                if (currentFilters[filterCode] !== '') {
                    splitCurrentValues.push(currentFilters[filterCode])
                }

                if (currentFilters[filterCode].split(PARAM_DELIMITER)[0] !== currentFilters[filterCode]) {
                    splitCurrentValues = currentFilters[filterCode].split(PARAM_DELIMITER);
                }

                if (input.is(":checked")) {
                    splitCurrentValues.push(value);
                } else {
                    let indexOf = $.inArray(value, splitCurrentValues);
                    if (indexOf !== -1) {
                        splitCurrentValues.splice(indexOf, 1);
                    } else {
                        console.error("Couldn't find " + value + " in current values while trying to remove it from there.")
                    }
                }

                currentFilters[filterCode] = splitCurrentValues.join(PARAM_DELIMITER);
                checkIfFiltersChanged()

                titleH3Div.text(getValuesCountText(splitCurrentValues.length, "Значение выбрано", "Значения выбрано", "Значений выбрано"))
            });

        groupDiv.append(label, input);

        input.checkboxradio();
    }

    groupDiv.controlgroup({
        direction: "vertical"
    });

    div.append(groupDiv)

    accordionDiv.append(titleH3, div);

    accordionDiv.accordion({
        collapsible: true,
        active: false,
        heightStyle: "content"
    })

    createFilterBase(filterCode, accordionDiv);
}

/**
 * Creates new filter based on its ID
 * @param filterCode ID of filter to create
 * @param initialValues Initial string value for filter to use
 */
function createFilter(filterCode, initialValues = "") {
    filtersData[filterCode].type.filterCreationMethod(filterCode, initialValues);
}

/**
 * Uses currentFilters for deleting all existing filter UI tools
 */
function removeAllFiltersUI() {
    for (const key of Object.keys(currentFilters)) {
        // console.log($("#" + key + "-filter"))
        $("#" + key + "-filter").remove();
    }
}

/**
 * Uses originalFilters field for build up all filters UI tools
 */
function createFiltersUIFromOriginal() {

    for (const [key, value] of Object.entries(originalFilters)) {
        createFilter(key, value)
    }

    appliedFiltersCountText.text(getFiltersCountText());
}

/**
 * Function for applying any changes made for filters
 * @returns {boolean}
 */
function applyCurrentFilters() {

    let isValid = true;
    for (const [key, value] of Object.entries(currentFilters)) {
        let isCurrentFilterValid = filtersData[key].validator(value);

        if (!isCurrentFilterValid) {
            $("#" + key + "-filter").removeClass("filter-row-not-valid").addClass("filter-row-not-valid")
            // console.warn(`Filter "${key}" has value "${value}" which is not valid. Check description of the filter.`);
        }

        isValid = isValid && isCurrentFilterValid;
    }

    if (!isValid) {
        $("#filter-validation-error").show().delay(5000).fadeOut();
        return false;
    } else {
        for (const key of Object.keys(filtersData)) {
            $("#" + key + "-filter").removeClass("filter-row-not-valid")
        }
    }


    copyCurrentFiltersToOrig();
    setFiltersChanged(false);

    appliedFiltersCountText.text(getFiltersCountText());

    let urlChanges = []
    for (const [key, value] of Object.entries(originalFilters)) {
        urlChanges.push(key + KEY_VALUE_DELIMITER + value);
    }
    changeURLByParamsList(LINK_PARAM_NAME, urlChanges);

    applyObserver.broadcast()

    return true;
}

/**
 * Function for canceling any changes made for filters
 */
function cancelCurrentFilters() {
    removeAllFiltersUI();
    restoreCurrentFiltersFromOrig();
    createFiltersUIFromOriginal();
    restoreAddButtonChoices();
    setFiltersChanged(false);

    if (Object.keys(originalFilters).length === 0) {
        $("#filters-list .content-wrapper").addClass("hidden");
        $("#no-filters-text").removeClass("hidden");
    } else {
        $("#filters-list .content-wrapper").removeClass("hidden");
        $("#no-filters-text").addClass("hidden");
    }
}

/**
 * Initialises all ui elements associated with filters
 */
function initBaseUI() {
    filtersShown.addClass("hidden");
    filtersList.addClass("hidden");
    filtersHidden.removeClass("hidden");

    $("#filter-validation-error").hide();

    applyFiltersButton.button()
        .removeClass("ui-button")
        .addClass("button_action")
        .on("click", () => {
            let hasApplied = applyCurrentFilters();

            if (hasApplied) {
                filtersShown.addClass("hidden");
                filtersList.addClass("hidden");
                filtersHidden.removeClass("hidden");
            }

        });

    setFiltersChanged(false);

    if (Object.keys(originalFilters).length === 0) {
        $("#filters-list .content-wrapper").addClass("hidden");
        $("#no-filters-text").removeClass("hidden");
    } else {
        $("#filters-list .content-wrapper").removeClass("hidden");
        $("#no-filters-text").addClass("hidden");
    }


    $("#btn-show-filters").button().removeClass("ui-button").addClass("button_action").on("click", () => {
        filtersHidden.addClass("hidden");
        filtersShown.removeClass("hidden");
        filtersList.removeClass("hidden");
    });

    $("#btn-cancel-filters").button().removeClass("ui-button").addClass("button_action").on("click", () => {
        filtersShown.addClass("hidden");
        filtersList.addClass("hidden");
        filtersHidden.removeClass("hidden");

        cancelCurrentFilters();
    })

    initAddButton();
}

/**
 * Function for un-disabling all choices in add button menu
 */
function restoreAddButtonChoices() {
    $("#filters-to-choose-select option").attr("disabled", false);

    for (const key of Object.keys(originalFilters)) {
        $("#" + key + "-option").attr("disabled", true);
    }

    $("#filters-to-choose-select").selectmenu("refresh")
}

/**
 * Initialises button for adding new filters.
 */
function initAddButton() {
    let isOpen = false;
    let selectmenu = $("#filters-to-choose-select").selectmenu({
        position: {
            my: "right top",
            at: "right bottom+5"
        },
        close: () => {
            isOpen = false;
        },
        open: () => {
            isOpen = true;
        },
        select: (event, data) => {
            let selectId = data.item.value;

            let attr = $("#" + selectId).attr("disabled");
            if (!isOpen || typeof attr !== 'undefined' && attr !== false && attr !== "") {
                return;
            }
            $("#" + selectId).attr("disabled", true);

            selectmenu.selectmenu("refresh");

            let filterId = selectId.replace("-option", "");
            createFilter(filterId);

            let noFiltersText = $("#no-filters-text");
            if (!noFiltersText.hasClass("hidden")) {
                $("#filters-list .content-wrapper").removeClass("hidden");
                noFiltersText.addClass("hidden");
            }

            if (Object.keys(currentFilters).length === Object.keys(filtersData).length) {
                selectmenu.selectmenu("disable");
            }
        }
    });
    $("#filters-to-choose-select-button .ui-selectmenu-text").remove();
    $("#filters-to-choose-select-button .ui-icon").remove();

    let plus = $("<div></div>").text("+").addClass("plus-text");
    $("#filters-to-choose-select-button").removeClass("ui-button").addClass("button_action").append(plus);

    let availableFiltersDict = {};

    let appliedFiltersList = Object.keys(originalFilters);

    for (const [key, value] of Object.entries(filtersData)) {
        availableFiltersDict[key] = {
            name: value.name,
            disabled: $.inArray(key, appliedFiltersList) !== -1
        };
    }

    let filters = [];

    for (const [key, value] of Object.entries(availableFiltersDict)) {

        if (value.disabled) {
            filters.push("<option id='" + key + "-option' value='" + key + "-option' disabled='disabled'>" + value.name + "</option>");
        } else {
            filters.push("<option id='" + key + "-option' value='" + key + "-option'>" + value.name + "</option>");
        }

    }

    selectmenu.append(filters.join("")).selectmenu("refresh");

}

/**
 * Main function for filters initialisation
 * @param receivedFiltersString string with filters received from url
 */
function initFilters(receivedFiltersString = '') {
    const re = /&amp;/gi;
    receivedFiltersString = receivedFiltersString.replace(re, "&");

    originalFilters = parseFiltersString(receivedFiltersString);

    restoreCurrentFiltersFromOrig();


    createFiltersUIFromOriginal();

    initBaseUI();
}

let appliedFiltersCountText = $("#filters-applied-count-text");

let filtersHidden = $("#filters-hidden");
let filtersShown = $("#filters-shown");
let filtersList = $("#filters-list");

let applyFiltersButton = $("#btn-apply-filters");


let applyObserver = new EventObserver();

let filtersChanged = false
let originalFilters = {}
let currentFilters = {}

// Различные данные для работы с фильтрами
let filtersData = {
    "training_id": {
        type: filterType.TEXT,
        name: "id тренировки",
        description: "Проверяется полное совпадение id тренировки с введенными данными. \n\nТребуется ввести текст, длиною ровно в 24 символа.",
        validator: (value) => {
            return value.length === 24
        },

        placeholder: "Полное совпадение"
    },
    "task_attempt_id": {
        type: filterType.TEXT,
        name: "id попытки",
        description: "Проверяется полное совпадение id попытки с введенными данными. \n\nТребуется ввести текст, длиною ровно в 24 символа.",
        validator: (value) => {
            return value.length === 24
        },

        placeholder: "Полное совпадение"
    },
    "username": {
        type: filterType.TEXT,
        name: "Логин",
        description: "Проверяется частичное совпадение логина с введенными данными. \n\nТребуется ввести текст, длиною не более 30 символов.",
        validator: (value) => {
            return value.length !== 0 && value.length <= 30
        },

        placeholder: "Частичное совпадение"
    },
    "full_name": {
        type: filterType.TEXT,
        name: "Имя",
        description: "Проверяется частичное совпадение имени с введенными данными. \n\nТребуется ввести текст, длиною не более 30 символов.",
        validator: (value) => {
            return value.length !== 0 && value.length <= 30
        },

        placeholder: "Частичное совпадение"
    },
    "presentation_record_duration": {
        type: filterType.RANGE,
        name: "Длительность аудиозаписи",
        description: "Проверяется, что длительность аудиозаписи находится в установленных пределах. \n\nОсобые требования отсутствуют.",
        validator: (value) => {
            return true
        },

        range_start: 0,
        range_end: 3599,
        step: 1,
        checkTextFormat: (string) => {
            return isInRecordDurationForm(string)
        },
        toStringMethod: (value) => {
            return recordDurationToString(value)
        },
        toValueMethod: (string) => {
            return recordDurationStringToSeconds(string)
        },
    },
    "training_start_timestamp":{
        type: filterType.DATE,
        name: "Начало тренировки",
        description: "Проверяется, что начало тренировки производилось в установленный период. \n\nОсобые требования отсутствуют.",
        validator: (value) => {
            return true
        },
    },
    "processing_start_timestamp": {
        type: filterType.DATE,
        name: "Начало обработки",
        description: "Проверяется, что начало обработки производилось в установленный период. \n\nОсобые требования отсутствуют.",
        validator: (value) => {
            return true
        },
    },
    "processing_finish_timestamp": {
        type: filterType.DATE,
        name: "Конец обработки",
        description: "Проверяется, что конец обработки производился в установленный период. \n\nОсобые требования отсутствуют.",
        validator: (value) => {
            return true
        },
    },
    "training_status": {
        type: filterType.CHOICE,
        name: "Статус тренировки",
        description: "Проверяется, является ли статус тренировки одним из выбранных значений. \n\nТребуется выбрать минимум одно значение.",
        validator: (value) => {
            return value !== ""
        },
        values: [
            "Новая тренировка",
            "В процессе",
            "Отправлена на распознавание",
            "Идёт распознавание",
            "Распознавание завершено",
            "Ошибка распознавания",
            "Отправлена на обработку",
            "Обрабатывается",
            "Обработана",
            "Ошибка обработки"
        ]
    },
    "audio_status": {
        type: filterType.CHOICE,
        name: "Статус аудио",
        description: "Проверяется, является ли статус аудио одним из выбранных значений. \n\nТребуется выбрать минимум одно значение.",
        validator: (value) => {
            return value !== ""
        },
        values: [
            "Новая аудиозапись",
            "Отправлена на распознавание",
            "Идёт распознавание",
            "Распознавание завершено",
            "Ошибка распознавания",
            "Отправлена на обработку",
            "Обрабатывается",
            "Обработана",
            "Ошибка обработки"
        ]
    },
    "presentation_status": {
        type: filterType.CHOICE,
        name: "Статус презентации",
        description: "Проверяется, является ли статус презентации одним из выбранных значений. \n\nТребуется выбрать минимум одно значение.",
        validator: (value) => {
            return value !== ""
        },
        values: [
            "Новая презентация",
            "Отправлена на распознавание",
            "Идёт распознавание",
            "Распознавание завершено",
            "Ошибка распознавания",
            "Отправлена на обработку",
            "Обрабатывается",
            "Обработана",
            "Ошибка обработки",
        ]

    },
    "pass_back_status": {
        type: filterType.CHOICE,
        name: "Статус отправки в LMS",
        description: "Проверяется, является ли статус отправки в LMS одним из выбранных значений. \n\nТребуется выбрать минимум одно значение.",
        validator: (value) => {
            return value !== ""
        },
        values: [
            "Не отправлена",
            "Отправлена",
            "Ошибка отправки"
        ]
    },
    "score": {
        type: filterType.RANGE,
        name: "Балл",
        description: "Проверяется, что балл находится в установленных пределах. \n\nОсобые требования отсутствуют.",
        validator: (value) => {
            return true
        },

        range_start: 0,
        range_end: 1,
        step: 0.01,
        checkTextFormat: (string) => {
            return isFloat(string)
        },
        toStringMethod: (value) => {
            return value.toString()
        },
        toValueMethod: (string) => {
            return parseFloat(string)
        }
    },
    "presentation_file_id": {
        type: filterType.TEXT,
        name: "Презентация",
        description: "Проверяется полное совпадение id презентации с введенными данными. \n\nТребуется ввести текст, длиною ровно в 24 символа.",
        validator: (value) => {
            return value.length === 24
        },

        placeholder: "Полное совпадение"
    },
}