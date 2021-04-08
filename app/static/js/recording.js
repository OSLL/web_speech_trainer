let gumStream,
    recorder,
    input,
    encodeAfterRecord,
    currentTimestamp;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then(function(stream) {
        callShowPage();
        currentTimestamp = Date.now();
        $('#tutorial')[0].style = "visibility: hidden; font-size: 0";
        $('#denoising-note')[0].style = "visibility: visible; font-size: 14";
        setTimeout(function () {
            $('#denoising-note')[0].style = "visibility: hidden; font-size: 0";
        }, 3000);
        let audioContext = new window.AudioContext();
        gumStream = stream;
        input = audioContext.createMediaStreamSource(stream);
        recorder = new WebAudioRecorder(input, {
            workerDir: "/static/js/libraries/WebAudioRecorder.js/",
            encoding: "mp3",
        });
        recorder.onComplete = function(recorder, blob) {
            $('#record-processing')[0].style = "visibility: hidden; font-size: 0";
            callAddPresentationRecord(blob);
        }
        recorder.setOptions({
            timeLimit: 3600,
            encodeAfterRecord: encodeAfterRecord,
            mp3: {bitRate: 160}
        });
        recorder.startRecording();
        $('#next')[0].disabled = false;
        $('#record')[0].disabled = true;
        $('#done')[0].disabled = false;
    });
}

function stopRecording() {
    gumStream.getAudioTracks()[0].stop();
    $('#record')[0].disabled = false;
    $('#record-processing')[0].style = "visibility: visible; font-size: 14px";
    recorder.finishRecording();
}

function callAddPresentationRecord(blob) {
    let fd = new FormData();
    fd.append('presentationRecord', blob);
    fd.append('trainingId', trainingId);
    fd.append('presentationRecordDuration', ((Date.now() - currentTimestamp) / 1000).toString());
    $.ajax({
      url: '/presentation_record',
      data: fd,
      processData: false,
      contentType: false,
      type: 'POST',
      datatype: 'json',
      success: function() {
          window.location.href = `/training_statistics/${trainingId}`;
      }
    });
}

$(document).ready(function() {
    encodeAfterRecord = true;
    $('#record').click(startRecording);
    $('#done').click(stopRecording);
    $('#record-processing')[0].style = "visibility: hidden; font-size: 0";
    $('#denoising-note')[0].style = "visibility: hidden; font-size: 0";
});
