(function () {
    // враппер над логами
    window.logWrapper = function (...args) {
        // стандартное логирование
        console.log(...args);

        // отправка на роут
        try {
            fetch('/logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: new Date().toISOString(),
                    message: args.map(a => a.toString()).join(' ')
                })
            });
        } catch (e) {
            console.error('Log send error', e);
        }
    }
})();