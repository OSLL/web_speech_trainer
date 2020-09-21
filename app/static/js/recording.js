var gumStream,
    rec,
    input,
    audioContext;

var recordButton = document.getElementById('record');

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(function(stream) {
        recordButton.textContent = "Recording...";
        audioContext = new window.AudioContext();
        gumStream = stream;
        input = audioContext.createMediaStreamSource(stream);
        rec = new Recorder(input, { numChannels: 2 });
        rec.record();
    });
}
recordButton.addEventListener('click', startRecording);

function stopRecording() {
    rec.stop();
    gumStream.getAudioTracks()[0].stop();
    rec.exportWAV(callAddPresentationRecord);
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
document.getElementById('done').addEventListener('click', stopRecording);
