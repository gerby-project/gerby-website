var simplemde = new SimpleMDE({
  autosave: {
    enabled: true,
    uniqueId: "comment-{{ tag.tag }}",
  },
  element: $("#comment")[0],
  forceSync: true,
  insertTexts: { link: ["\\ref{", "}"] },
  placeholder: "You can type your comment here, use the preview option to see what it will look like.",
  previewRender: function(plaintext, preview) {
    // asynchronous
    plaintext = plaintext.replace(/\\ref\{([0-9A-Z]{4})\}/g, "[$1](/tag/$1)");
    output = this.parent.markdown(plaintext);

    setTimeout(function() {
      preview.innerHTML = output;
      MathJax.Hub.Queue(["Typeset", MathJax.Hub]);//, $("div.editor-preview, div.editor-preview-side")]);
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

