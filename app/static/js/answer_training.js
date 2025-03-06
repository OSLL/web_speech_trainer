let questions = []
let questionsTime = []
let currentQuestionIndex = 0
let timer
let timeLeft

let gumStream,
    recorder,
    input,
    encodeAfterRecord = true,
    currentTimestamp
let isRecording = false
let isRecordingCompleted = false

$(document).ready(function() {
    let timerElement = $('#timer')
    let questionElement = $('#question')
    let questionsCountElement = $('#questions-count')
    let nextButton = $('#next-button')
    let retryButton = $('#retry-button')
    let startRecordingButton = $('#start-recording-button')

    function fetchQuestionsAndTime() {
        $.ajax({
            url: '/api/get_questions_and_time/',
            method: 'GET',
            dataType: 'json',
            success: function(data) {
                questions = data.questions.map(q => q.text)
                questionsTime = data.questions.map(q => q.time_for_answer)
                updateQuestion()
            },
            error: function(error) {
                console.error('Error fetching questions and time:', error)
            }
        })
    }

    function startRecording() {
        if (isRecording) return
        isRecording = true
        isRecordingCompleted = false
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
                    nextButton.removeAttr('disabled')
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
                retryButton.attr('disabled', 'true')
            })
            .catch(function(err) {
                isRecording = false
            })
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
        timeLeft = questionsTime[currentQuestionIndex]
        timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
    }

    function startTimer() {
        timeLeft = questionsTime[currentQuestionIndex]
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
        timeLeft = questionsTime[currentQuestionIndex]
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

    function retryQuestion() {
        clearInterval(timer)
        isRecording = false
        isRecordingCompleted = false
        timeLeft = questionsTime[currentQuestionIndex]
        timerElement.html(`<p>Таймер: ${timeLeft} сек</p>`)
    }

    function finish() {
        alert('stop')
    }

    startRecordingButton.on('click', startRecording)
    nextButton.on('click', nextQuestion)
    retryButton.on('click', retryQuestion)

    fetchQuestionsAndTime()
})