function getTrainingIdFromUrl() {
    // попытка URL с id: /trainings/<training_id>/, /trainings/statistics/<training_id>/
    const match = window.location.pathname.match(/\/trainings(?:\/statistics)?\/([0-9a-fA-F]{24})\//);
    return match ? match[1] : null;
}

(function () {

    // const trainingId =
    //     window.APP_CONTEXT?.trainingId ?? null;

    class Logger {

        log(...args) {

            const trainingId = getTrainingIdFromUrl();

            console.log(...args);

            fetch('/logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    timestamp: new Date().toISOString(),
                    message: args.join(' '),
                    trainingId: trainingId
                })
            });
        }
    }

    window.logger = new Logger();
})();