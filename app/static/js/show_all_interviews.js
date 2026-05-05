(function () {
    function parseIntData(value, fallback) {
        var parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function buildUrl(baseUrl, params) {
        var url = new URL(baseUrl, window.location.origin);

        Object.keys(params).forEach(function (key) {
            var value = params[key];
            if (value !== null && value !== undefined && String(value).trim() !== '') {
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
        link.href = disabled ? '#' : buildUrl(baseUrl, Object.assign({}, baseParams, { page: targetPage }));
    }

    function initPagination() {
        var pagination = document.getElementById('interviewsPagination');
        if (!pagination) {
            return;
        }

        var currentPage = parseIntData(pagination.dataset.currentPage, 0);
        var pageCount = parseIntData(pagination.dataset.pageCount, 1);
        var count = parseIntData(pagination.dataset.count, 10);
        var baseUrl = pagination.dataset.baseUrl || window.location.pathname;
        var baseParams = {
            username: pagination.dataset.username || '',
            q: pagination.dataset.query || '',
            count: count
        };

        var prevItem = pagination.querySelector('[data-pagination-item="prev"]');
        var nextItem = pagination.querySelector('[data-pagination-item="next"]');
        var prevLink = pagination.querySelector('[data-pagination-link="prev"]');
        var nextLink = pagination.querySelector('[data-pagination-link="next"]');
        var label = pagination.querySelector('[data-pagination-label]');

        setPaginationItem(prevItem, prevLink, currentPage - 1, currentPage <= 0, baseParams, baseUrl);
        setPaginationItem(nextItem, nextLink, currentPage + 1, currentPage + 1 >= pageCount, baseParams, baseUrl);

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

    function initFilterForm() {
        var form = document.getElementById('interviewsFilterForm');
        var resetButton = document.getElementById('interviewsSearchReset');
        var input = document.getElementById('interviewsSearchInput');

        if (form && input) {
            form.addEventListener('submit', function () {
                input.value = input.value.trim();
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

    document.addEventListener('DOMContentLoaded', function () {
        initPagination();
        initEmptyState();
        initFilterForm();
    });
})();
