$(document).ready(function() {
  // toggle for comments
  $("section#post-comment h2 ~ *").toggle();
  $("section#post-comment > h2").css("cursor", "pointer");
  $("section#post-comment h2").addClass("hidden");

  $("section#post-comment h2").on("click", function() {
    $("section#post-comment h2").toggleClass("hidden");
    $("section#post-comment h2 ~ *").toggle();

    localStorage.setItem("comment-visible", !($("section#post-comment h2").hasClass("hidden")));
  });

  if (localStorage.getItem("comment-visible") == "true")
    $("section#post-comment h2").click();

  // read author information from local storage
  $("input#name").val(localStorage.getItem("name"));
  $("input#mail").val(localStorage.getItem("mail"));
  $("input#site").val(localStorage.getItem("site"));
});

