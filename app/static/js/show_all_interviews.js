(function () {
    function parseIntData(value, fallback) {
        var parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function normalizeValue(value) {
        return String(value || '').trim();
    }

    function normalizeScoreValue(value) {
        return normalizeValue(value).replace(',', '.');
    }

    function buildUrl(baseUrl, params) {
        var url = new URL(baseUrl, window.location.origin);

        Object.keys(params).forEach(function (key) {
            var value = normalizeValue(params[key]);

            if (value) {
                url.searchParams.set(key, value);
            }
        });

        return url.pathname + url.search;
    }

    function setPaginationItem(item, link, targetPage, disabled, baseParams, baseUrl) {
        if (!item || !link) {
            return;
        }

        item.classList.toggle('disabled', disabled);
        link.setAttribute('aria-disabled', disabled ? 'true' : 'false');
        link.tabIndex = disabled ? -1 : 0;
        link.href = disabled ? '#' : buildUrl(
            baseUrl,
            Object.assign({}, baseParams, { page: targetPage })
        );
    }

    function getPaginationBaseParams(pagination) {
        return {
            username: pagination.dataset.username || '',
            full_name: pagination.dataset.fullName || '',
            user_query: pagination.dataset.userQuery || '',
            score_gt: pagination.dataset.scoreGt || '',
            count: pagination.dataset.count || '10'
        };
    }

    function initPagination() {
        var pagination = document.getElementById('interviewsPagination');

        if (!pagination) {
            return;
        }

        var currentPage = parseIntData(pagination.dataset.currentPage, 0);
        var pageCount = Math.max(parseIntData(pagination.dataset.pageCount, 1), 1);
        var baseUrl = pagination.dataset.baseUrl || window.location.pathname;
        var baseParams = getPaginationBaseParams(pagination);

        var prevItem = pagination.querySelector('[data-pagination-item="prev"]');
        var nextItem = pagination.querySelector('[data-pagination-item="next"]');
        var prevLink = pagination.querySelector('[data-pagination-link="prev"]');
        var nextLink = pagination.querySelector('[data-pagination-link="next"]');
        var label = pagination.querySelector('[data-pagination-label]');

        setPaginationItem(
            prevItem,
            prevLink,
            currentPage - 1,
            currentPage <= 0,
            baseParams,
            baseUrl
        );

        setPaginationItem(
            nextItem,
            nextLink,
            currentPage + 1,
            currentPage + 1 >= pageCount,
            baseParams,
            baseUrl
        );

        if (label) {
            label.textContent = 'Страница ' + (currentPage + 1) + ' из ' + pageCount;
        }
    }

    function initEmptyState() {
        var tableWrap = document.querySelector('.interviews-table-wrap');
        var empty = document.querySelector('.interviews-empty');
        var pagination = document.getElementById('interviewsPagination');

        if (!tableWrap || !empty) {
            return;
        }

        var rowsCount = tableWrap.querySelectorAll('tbody tr').length;
        var hasRows = rowsCount > 0;

        tableWrap.hidden = !hasRows;
        empty.hidden = hasRows;

        if (pagination) {
            pagination.hidden = !hasRows;
        }
    }

    function validateScoreInput(input) {
        if (!input) {
            return true;
        }

        var normalized = normalizeScoreValue(input.value);

        if (!normalized) {
            input.setCustomValidity('');
            return true;
        }

        var validFormat = /^\d+(\.\d+)?$/.test(normalized);
        var parsed = Number(normalized);
        var valid = validFormat && Number.isFinite(parsed) && parsed >= 0 && parsed <= 1;

        input.setCustomValidity(valid ? '' : 'Введите число от 0 до 1, например 0.7');

        return valid;
    }

    function trimFormInputs(form) {
        form.querySelectorAll('input[type="search"]').forEach(function (input) {
            input.value = normalizeValue(input.value);
        });

        var scoreInput = document.getElementById('interviewsScoreGtInput');

        if (scoreInput) {
            scoreInput.value = normalizeScoreValue(scoreInput.value);
        }
    }

    function initFilterForm() {
        var form = document.getElementById('interviewsFilterForm');
        var resetButton = document.getElementById('interviewsSearchReset');
        var scoreInput = document.getElementById('interviewsScoreGtInput');

        if (scoreInput) {
            scoreInput.addEventListener('input', function () {
                validateScoreInput(scoreInput);
            });
        }

        if (form) {
            form.addEventListener('submit', function (event) {
                trimFormInputs(form);

                if (!validateScoreInput(scoreInput)) {
                    event.preventDefault();
                    form.reportValidity();
                }
            });
        }

        if (resetButton) {
            resetButton.addEventListener('click', function () {
                var baseUrl = resetButton.dataset.baseUrl || window.location.pathname;
                var usernameInput = form ? form.querySelector('input[name="username"]') : null;
                var countInput = form ? form.querySelector('input[name="count"]') : null;

                window.location.href = buildUrl(baseUrl, {
                    username: usernameInput ? usernameInput.value : '',
                    count: countInput ? countInput.value : '',
                    page: 0
                });
            });
        }
    }

    function createResultsLink(resultsUrl) {
        var link = document.createElement('a');
        link.className = 'btn btn-sm btn-outline-primary';
        link.href = resultsUrl;
        link.textContent = 'Открыть';
        return link;
    }

    function renderEmptyResultsCell(cell) {
        cell.textContent = '—';
    }

    function renderResultsCell(cell) {
        var resultsUrl = normalizeValue(cell.dataset.resultsUrl);

        cell.innerHTML = '';

        if (!resultsUrl) {
            renderEmptyResultsCell(cell);
            return;
        }

        cell.appendChild(createResultsLink(resultsUrl));
    }

    function initResultsLinks() {
        document.querySelectorAll('.interview-results-cell').forEach(renderResultsCell);
    }

    document.addEventListener('DOMContentLoaded', function () {
        initPagination();
        initEmptyState();
        initFilterForm();
        initResultsLinks();
    });
})();