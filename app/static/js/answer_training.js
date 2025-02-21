let questions = [
    'Вопрос 1?',
    'Вопрос 2?',
    'Вопрос 3?',
    'Вопрос 4?',
    'Вопрос 5?'
]
let currentQuestionIndex = 0
let timer
let timeLeft = 60

let gumStream,
    recorder,
    input,
    encodeAfterRecord = true,
    currentTimestamp

document.addEventListener('DOMContentLoaded', function() {
    let timerElement = document.getElementById('timer')
    let questionElement = document.getElementById('question')
    let questionsCountElement = document.getElementById('questions-count')
    let nextButton = document.getElementById('next-button')
    let retryButton = document.getElementById('retry-button')
    let startRecordingButton = document.getElementById('start-recording-button')


    function startRecording() {
        alert('startRecording')
    }

    function startTimer() {
        timeLeft = 60
        timerElement.innerHTML = `<p>Таймер: ${timeLeft} сек</p>`
        timer = setInterval(function() {
            timeLeft--
            timerElement.innerHTML = `<p>Таймер: ${timeLeft} сек</p>`
            if (timeLeft <= 0) {
                clearInterval(timer)
                nextQuestion()
            }
        }, 1000)
    }

    function nextQuestion() {
        clearInterval(timer)
        currentQuestionIndex++
        if (currentQuestionIndex >= questions.length) {
            finishQuiz()
        } else {
            updateQuestion()
            startTimer()
        }
    }

    function updateQuestion() {
        questionElement.innerHTML = `<p>${questions[currentQuestionIndex]}</p>`
        questionsCountElement.innerHTML = `<p>Вопрос ${currentQuestionIndex + 1} из ${questions.length}</p>`
        if (currentQuestionIndex === questions.length - 1) {
            nextButton.innerHTML = 'Завершить'
            nextButton.removeEventListener('click', nextQuestion)
            nextButton.addEventListener('click', finish)
        } else {
            nextButton.innerHTML = 'Следующий вопрос'
            nextButton.removeEventListener('click', finish)
            nextButton.addEventListener('click', nextQuestion)
        }
    }

    function retryQuestion() {
        clearInterval(timer)
        startTimer()
    }

    function finish() {
        alert('stop')
    }

    startRecordingButton.addEventListener('click', startRecording)
    nextButton.addEventListener('click', nextQuestion)
    retryButton.addEventListener('click', retryQuestion)

    updateQuestion()
    startTimer()
});