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

const fileInput = document.getElementById('avatar-file-input');
const avatarContainer = document.getElementById('avatar-container');

if (fileInput) {
    fileInput.addEventListener('change', async (ev) => {
        const file = ev.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('video/')) {
            alert('Пожалуйста, выберите видео-файл.');
            return;
        }

        const form = new FormData();
        form.append('file', file);

        try {
            const res = await fetch('/upload_avatar', {
                method: 'POST',
                body: form
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                alert('Ошибка загрузки: ' + (data.error || data.message || res.statusText));
                return;
            }
            const videoUrl = '/avatar_video?t=' + Date.now();

            let videoEl = document.getElementById('avatar-video');
            const placeholder = document.getElementById('avatar-placeholder');

            if (!videoEl) {
                if (placeholder) placeholder.remove();

                videoEl = document.createElement('video');
                videoEl.id = 'avatar-video';
                videoEl.className = 'avatar-stream';
                videoEl.autoplay = true;
                videoEl.loop = true;
                videoEl.muted = true;
                videoEl.playsInline = true;
                videoEl.src = videoUrl;
                avatarContainer.appendChild(videoEl);
            } else {
                videoEl.src = videoUrl;
                videoEl.load();
            }
            videoEl.play().catch((e) => {
                console.log('video play blocked:', e);
            });

            alert('Аватар загружен и обновлён.');

        } catch (err) {
            console.error(err);
            alert('Ошибка при загрузке файла.');
        } finally {
            fileInput.value = '';
        }
    });
}
