from flask import redirect, render_template, request

from gerby.gerby import app
from gerby.database import *


@app.route("/search", methods = ["GET"])
def show_search():
  # TODO not sure whether this is an efficient query: only fulltext and docid is quick apparently
  # TODO can we use TagSearch.docid and Tag.rowid or something?
  # TODO can we match on a single column? maybe we need two tables?

  # TODO suggestion by Max: make sure that if someone searches for a tag in the search field, you return the tag
  # = get rid of the tag lookup field
  # TODO suggestion by Brian: implement different spellings of words, à la Google

  # return empty page (for now)
  if "query" not in request.args:
    return render_template("show_search.html", results=[])

  # it might be a tag!
  if len(request.args["query"]) == 4:
    tag = Tag.select(Tag.tag).where(Tag.tag == request.args["query"])
    if tag.count() == 1:
      return redirect("tag/" + request.args["query"])

  results = Tag.select(Tag, TagSearch, TagSearch.rank().alias("score")).join(TagSearch, on=(Tag.tag == TagSearch.tag).alias("search")).where(TagSearch.match(request.args["query"]), Tag.type.not_in(["chapter", "section", "subsection"]))
  results = sorted(results)
  return render_template("show_search.html", results=results)

