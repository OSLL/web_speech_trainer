let questions = []
let questionsAudio = []
let currentQuestionIndex = 0
let questionsTime
let timer
let timeLeft

let gumStream,
    recorder,
    input,
    encodeAfterRecord = true,
    currentTimestamp,
    trainingId
let isRecording = false
let isRecordingCompleted = false

function setupTraining(trainingId_) {
    trainingId = trainingId_
}

$(document).ready(function() {
    let timerElement = $('#timer')
    let questionElement = $('#question')
    let questionsCountElement = $('#questions-count')
    let nextButton = $('#next-button')
    let retryButton = $('#retry-button')
    let startRecordingButton = $('#start-recording-button')
    let listenQuestionButton = $('#listen-question-button')

    function fetchQuestionsAndTime() {
        const sec = 60
        const count = 5

        $.ajax({
            url: `/api/get_questions_and_time/${trainingId}/?sec=${sec}&count=${count}`,
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                questions = data.questions.map(q => q.text)
                questionsAudio = data.questions.map(q => q.audio_url)
                questionsTime = data.sec
                updateQuestion()
            },
            error: function(error) {
                console.error('Error:', error)
            }
        })
    }

    function startRecording() {
        if (isRecording) return
        isRecording = true
        isRecordingCompleted = false
        retryButton.attr('disabled', 'true')
        currentTimestamp = Date.now()
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function(stream) {
                gumStream = stream
                let audioContext = new (window.AudioContext || window.webkitAudioContext)()
                input = audioContext.createMediaStreamSource(stream)
                recorder = new WebAudioRecorder(input, {
                    workerDir: "/static/js/libraries/WebAudioRecorder.js/",
                    encoding: "mp3",
                })

                recorder.onComplete = function(recorder, blob) {
                    isRecordingCompleted = true
                    startRecordingButton.text('Начать запись').off('click').on('click', startRecording)
                    nextButton.removeAttr('disabled')
                    retryButton.removeAttr('disabled')
                    saveRecording(blob)
                }

                recorder.setOptions({
                    timeLimit: 120,
                    encodeAfterRecord: encodeAfterRecord,
                    ogg: { quality: 0.5 },
                    mp3: { bitRate: 160 }
                })

                recorder.startRecording()
                startTimer()
                startRecordingButton.text('Закончить запись').off('click').on('click', stopRecording)
                nextButton.attr('disabled', 'true')
            })
            .catch(function(err) {
                isRecording = false
                retryButton.removeAttr('disabled')
            })
    }

    function playQuestionAudio() {
        const audioUrl = questionsAudio[currentQuestionIndex]
        if (!audioUrl) {
            console.error('Audio URL not found for the current question.')
            return
        }

        const audio = new Audio(audioUrl)
        startRecordingButton.attr('disabled', 'true')

        audio.play()
            .then(() => {
                audio.onended = () => {
                    startRecordingButton.removeAttr('disabled')
                }
            })
            .catch(err => console.error('Error playing audio:', err))
    }

    function stopRecording() {
        if (!isRecording) return
        clearInterval(timer)
        isRecording = false
        recorder.finishRecording()
        gumStream.getAudioTracks()[0].stop()
        startRecordingButton.text('Начать запись').off('click').on('click', startRecording)
        nextButton.removeAttr('disabled')
        retryButton.removeAttr('disabled')
        timeLeft = questionsTime
        timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
    }

    function startTimer() {
        timeLeft = questionsTime
        timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
        timer = setInterval(function() {
            timeLeft--
            timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
            if (timeLeft <= 0) {
                clearInterval(timer)
                nextQuestion()
            }
        }, 1000)
    }

    function nextQuestion() {
        if (!isRecordingCompleted) return
        clearInterval(timer)
        isRecording = false
        isRecordingCompleted = false
        currentQuestionIndex++
        if (currentQuestionIndex >= questions.length) {
            finishQuiz()
        } else {
            updateQuestion()
        }
    }

    function updateQuestion() {
        timeLeft = questionsTime
        timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
        questionElement.html(`<p>${questions[currentQuestionIndex]}</p>`)
        questionsCountElement.html(`<p>Вопрос ${currentQuestionIndex + 1} из ${questions.length}</p>`)
        if (currentQuestionIndex === questions.length - 1) {
            nextButton.text('Завершить').off('click').on('click', finish)
        } else {
            nextButton.text('Следующий вопрос').off('click').on('click', nextQuestion)
        }
        nextButton.attr('disabled', 'true')
    }

    function saveRecording(blob) {
        let fd = new FormData()
        fd.append("answerRecord", blob)
        fd.append("answerRecordDuration", ((Date.now() - currentTimestamp) / 1000).toString())
        fetch(`/api/answer_training/records/${trainingId}/`, {method: "POST", body: fd})
        // .then(response => console.log(response))
    }

    function finish() {
        if (!trainingId) {
            console.error("trainingId is not defined.")
            return
        }
        window.location.href = `/answer_training/statistics/${trainingId}/`
    }

    startRecordingButton.on('click', startRecording)
    nextButton.on('click', nextQuestion)
    retryButton.on('click', playQuestionAudio)

    fetchQuestionsAndTime()
})