$(document).ready(function() {
    $.ajax({
      url: '/get_all_trainings',
      contentType: false,
      type: 'GET',
      datatype: 'json',
      success: function (response) {
          console.log(response)
      }
    });
});
