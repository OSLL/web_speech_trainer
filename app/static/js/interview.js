let timerElement = document.getElementById("timer");
let startBtn = document.getElementById("start-btn");
let stopBtn = document.getElementById("stop-btn");

let seconds = 0;
let timer = null;

function updateTimer() {
    let mins = Math.floor(seconds / 60);
    let secs = seconds % 60;
    timerElement.textContent =
        `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

startBtn?.addEventListener("click", () => {
    if (timer) return;
    timer = setInterval(() => {
        seconds++;
        updateTimer();
    }, 1000);
});

stopBtn?.addEventListener("click", () => {
    if (confirm("Вы уверены, что хотите прервать сессию?")) {
        clearInterval(timer);
        timer = null;
        seconds = 0;
        updateTimer();
    }
});
