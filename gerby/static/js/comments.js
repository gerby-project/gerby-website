$(document).ready(function() {
  // toggle for comments
  $("section#post-comment h2 ~ *").toggle();
  $("section#post-comment > h2").css("cursor", "pointer");
  $("section#post-comment h2").addClass("hidden");

  $("section#post-comment h2").on("click", function() {
    $("section#post-comment h2").toggleClass("hidden"); // can we do this in a one-liner?
    $("section#post-comment h2 ~ *").toggle();
  });
});

