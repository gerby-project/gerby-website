from flask import redirect, render_template, request

from gerby.gerby import app
from gerby.views import tag
from gerby.database import *

import peewee

spelling = {
    "quasicoherent": "\"quasi-coherent\"",
    "quasicompact": "\"quasi-compact\""
    }

@app.route("/search", methods = ["GET"])
def show_search():
  # TODO not sure whether this is an efficient query: only fulltext and docid is quick apparently
  # TODO can we use TagSearch.docid and Tag.rowid or something?
  # TODO can we match on a single column? maybe we need two tables?
  page = 1
  if "page" in request.args:
    page = int(request.args["page"])

  perpage = 10
  if "perpage" in request.args:
    if request.args["perpage"] == "oo":
      perpage = 9223372036854775807 # 2^63-1 (shame on me for taking this approach)
    else:
      perpage = int(request.args["perpage"])


  # return empty page (for now)
  if "query" not in request.args:
    return render_template("search.html", count=0, perpage=perpage)

  # if the query is actually a tag we redirect
  if tag.isTag(request.args["query"]) and Tag.select().where(Tag.tag == request.args["query"].upper()).exists():
    return redirect("tag/" + request.args["query"].upper())

  # nope, we perform a search instead
  tags = [result.tag for result in TagSearch(TagSearch.tag).search(request.args["query"])]

  try:
    results = Tag.select().where(Tag.tag << tags, ~(Tag.type << ["item"])) # TODO search options go here: only search for sections, or only statements, etc.
    count = results.count()
  except peewee.OperationalError as e:
    if "too many SQL variables" in str(e):
      return render_template("search.html",
                             query=request.args["query"],
                             count=-1)

  # sorting and pagination
  results = sorted(results)
  results = results[(page - 1) * perpage : page * perpage]

  # determine list of parents
  references = set()
  for result in results:
    pieces = result.ref.split(".")
    references.update([".".join(pieces[0:i]) for i in range(len(pieces) + 1)])

  # get all tags for the search results (including parent tags)
  complete = Tag.select() \
                .where(Tag.ref << references, ~(Tag.type << ["item", "part"]))
  tree = tag.combine(list(sorted(complete)))

  # check whether we should suggest an alternative query, and build it if this is the case
  misspellt = [keyword for keyword in spelling.keys() if keyword in request.args["query"]]
  alternative = request.args["query"]

  if len(results) == 0 and len(misspellt) != 0:
    for keyword in misspellt:
      alternative = alternative.replace(keyword, spelling[keyword])

  return render_template("search.html",
                         query=request.args["query"],
                         count=count,
                         page=page,
                         perpage=perpage,
                         tree=tree,
                         misspellt=misspellt,
                         alternative=alternative,
                         headings=tag.headings)

