from flask import redirect, render_template, request

from gerby.gerby import app
from gerby.views import tag
from gerby.database import *


@app.route("/search", methods = ["GET"])
def show_search():
  # TODO not sure whether this is an efficient query: only fulltext and docid is quick apparently
  # TODO can we use TagSearch.docid and Tag.rowid or something?
  # TODO can we match on a single column? maybe we need two tables?

  # TODO we need to have complete (sub)sections and chapters in the database: we don't want to collate these things on the fly! (this is to be done in tools/)

  # TODO suggestion by Brian: implement different spellings of words, à la Google

  # return empty page (for now)
  if "query" not in request.args:
    return render_template("search.html", count=0)

  # it might be a tag!
  if tag.isTag(request.args["query"]):
    return redirect("tag/" + request.args["query"])

  # nope, we perform a search instead
  tags = [result.tag for result in TagSearch(TagSearch.tag).search(request.args["query"])]

  results = Tag.select() \
               .where(Tag.tag << tags, ~(Tag.type << tag.headings))

  references = set()
  for result in results:
    pieces = result.ref.split(".")
    references.update([".".join(pieces[0:i]) for i in range(len(pieces) + 1)])

  complete = Tag.select() \
                .where(Tag.ref << references, ~(Tag.type << ["item"]))

  tree = tag.combine(list(sorted(complete)))
  return render_template("search.html",
                         query=request.args["query"],
                         count=len(results),
                         tree=tree,
                         headings=tag.headings)

