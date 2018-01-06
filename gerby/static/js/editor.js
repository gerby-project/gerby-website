var simplemde = new SimpleMDE({
  autosave: {
    enabled: true,
    delay: 1000,
    uniqueId: "comment-{{ tag.tag }}",
  },
  element: $("#comment")[0],
  forceSync: true,
  insertTexts: { link: ["\\ref{", "}"], inline: ["$", "$"], display: ["$$", "$$"] },
  placeholder: "You can type your comment here, use the preview option to see what it will look like.",
  previewRender: function(plaintext, preview) {
    // deal with references
    plaintext = plaintext.replace(/\\ref\{([0-9A-Z]{4})\}/g, "[$1](/tag/$1)");
    // deal with \[\] getting replaced to []
    plaintext = plaintext.replace(/\\\[/g, "\\begin{equation}");
    plaintext = plaintext.replace(/\\\]/g, "\\end{equation}");

    output = this.parent.markdown(plaintext);

    setTimeout(function() {
      preview.innerHTML = output;
      MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
    }, 0);

    return "";
  },
  spellChecker: false,
  status: false,
  toolbar: [
    "link", "|",
    "bold", "italic", "|",
    "ordered-list", "unordered-list", "|",
    "preview"
  ],
});

// make sure to show tags, not numbers
simplemde.codemirror.on("change", function() {
  $("input#burger-toggle-tags").click();
});

// remove the event listener that forgets a comment on submit
simplemde.element.form.removeEventListener("submit", function() {
	localStorage.removeItem("smde_" + simplemde.options.autosave.uniqueId);
});
