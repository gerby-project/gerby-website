$(document).ready(function() {
  $("pre.commit-message").toggle();
  $("table#history td:first-child").css("cursor", "pointer");
  //$("table#history td:first-child").prepend("<span style='float: right'>+</span>");
  $("table#history td:first-child").click(function() {
    $(this).find("pre.commit-message").toggle();
    $(this).toggleClass("clicked");
  });
});

