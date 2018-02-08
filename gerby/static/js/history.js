$(document).ready(function() {
  $("table#history tbody tr:nth-child(even)").toggle();
  $("table#history tr:nth-child(odd) td:first-child").css("cursor", "pointer");

  $("table#history tr:nth-child(odd) td:first-child").click(function() {
    $(this).parent().next().toggle();
    $(this).toggleClass("clicked");
  });
});

