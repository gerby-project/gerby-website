$(document).ready(function() {
  // toggle for comments
  $("section#post-comment h2 ~ *").toggle();
  $("section#post-comment > h2").css("cursor", "pointer");
  $("section#post-comment h2").addClass("hidden");

  $("section#post-comment h2").on("click", function() {
    $("section#post-comment h2").toggleClass("hidden");
    $("section#post-comment h2 ~ *").toggle();

    Cookies.set("comment-visible", !($("section#post-comment h2").hasClass("hidden")));
  });

  if (Cookies.get("comment-visible") == "true")
    $("section#post-comment h2").click();
});

