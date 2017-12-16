from flask import redirect, render_template, request

from gerby.gerby import app
from gerby.views import tag
from gerby.database import *

spelling = {
    "quasicoherent": "quasi-coherent",
    "quasicompact": "quasi-compact"
    }

@app.route("/search", methods = ["GET"])
def show_search():
  # TODO not sure whether this is an efficient query: only fulltext and docid is quick apparently
  # TODO can we use TagSearch.docid and Tag.rowid or something?
  # TODO can we match on a single column? maybe we need two tables?

  # TODO we need to have complete (sub)sections and chapters in the database: we don't want to collate these things on the fly! (this is to be done in tools/)

  # return empty page (for now)
  if "query" not in request.args:
    return render_template("search.html", count=0)

  # if the query is actually a tag we redirect
  if tag.isTag(request.args["query"]) and Tag.select().where(Tag.tag == request.args["query"].upper()).exists():
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

  # check whether we should suggest an alternative query, and build it if this is the case
  misspellt = [keyword for keyword in spelling.keys() if keyword in request.args["query"]]
  alternative = request.args["query"]

  if len(results) == 0 and len(misspellt) != 0:
    for keyword in misspellt:
      alternative = alternative.replace(keyword, spelling[keyword])

  return render_template("search.html",
                         query=request.args["query"],
                         count=len(results),
                         tree=tree,
                         misspellt=misspellt,
                         alternative=alternative,
                         headings=tag.headings)

