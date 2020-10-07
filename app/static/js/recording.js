var gumStream,
    recorder,
    input,
    encodeAfterRecord;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(function(stream) {
        audioContext = new window.AudioContext();
        gumStream = stream;
        input = audioContext.createMediaStreamSource(stream);
        recorder = new WebAudioRecorder(input, {
            workerDir: "static/js/libraries/WebAudioRecorder.js/",
            encoding: "mp3",
        });
        recorder.onComplete = function(recorder, blob) {
            createDownloadLink(blob);
            callAddPresentationRecord(blob);
        }
        recorder.setOptions({
            timeLimit: 3600,
            encodeAfterRecord: encodeAfterRecord,
            mp3: {bitRate: 160}
        });
        recorder.startRecording();
    });
    $('#record')[0].disabled = true;
    $('#stop')[0].disabled = false;
}

function stopRecording() {
    gumStream.getAudioTracks()[0].stop();
    $('#stop')[0].disabled = true;
    $('#record')[0].disabled = false;
    recorder.finishRecording();
}

function createDownloadLink(blob) {
    var url = window.URL.createObjectURL(blob);
    var audio = document.createElement('audio');
    var record = document.createElement('li');
    var link = document.createElement('a');
    audio.controls = true;
    audio.src = url;
    link.href = url;
    link.download = 'audio.mp3';
    link.innerHTML = 'Download';
    record.appendChild(audio);
    record.appendChild(link);
    $('#record_div')[0].appendChild(record);
}

function callAddPresentationRecord(blob) {
    var fd = new FormData();
    fd.append('presentationRecord', blob);
    fd.append('presentationFileId', presentationFileId);

    $.ajax({
      url: '/presentation_record',
      data: fd,
      processData: false,
      contentType: false,
      type: 'POST'
    });
}

$(document).ready(function() {
    encodeAfterRecord = true;
    $('#record').click(startRecording);
    $('#stop').click(stopRecording);
});
