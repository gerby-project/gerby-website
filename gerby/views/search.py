from flask import redirect, render_template, request

from gerby.application import app
from gerby.views import tag
from gerby.database import *

import peewee

spelling = {
    "quasicoherent": "\"quasi-coherent\"",
    "quasicompact": "\"quasi-compact\"",
    "quasiisomorphism": "\"quasi-isomorphism\"",
    "quasiisomorphic": "\"quasi-isomorphic\"",

    "semilocal": "\"semi-local\"",
    "semicontinuous": "\"semi-continuous\"",

    "pseudocoherent": "\"pseudo-coherent\"",
    }
extras = {"slogan": Slogan, "history": History, "reference": Reference}

@app.route("/tag")
def redirect_to_search():
  return redirect("/search")

@app.route("/search", methods = ["GET"])
def show_search():
  # dealing with search options: page number
  page = 1
  if "page" in request.args:
    page = int(request.args["page"])

  # dealing with search options: page size
  perpage = 10
  if "perpage" in request.args:
    if request.args["perpage"] == "oo":
      perpage = 9223372036854775807 # 2^63-1 (shame on me for taking this approach)
    else:
      perpage = int(request.args["perpage"])

  # dealing with search options: search radius (all tags, only statements)
  radius = "all"
  if "radius" in request.args and request.args["radius"] == "statements":
    radius = "statements"


  # a) return empty page (for now)
  if "query" not in request.args:
    return render_template("search.html", count=0, perpage=perpage, radius="all")


  # b) if the query is actually a tag we redirect
  if tag.isTag(request.args["query"]) and Tag.select().where(Tag.tag == request.args["query"].upper()).exists():
    return redirect("tag/" + request.args["query"].upper())


  # c) actually search
  try:
    if radius == "all":
      tags = [result.tag for result in SearchTag(SearchTag.tag).search(request.args["query"])]
    else:
      tags = [result.tag for result in SearchStatement(SearchStatement.tag).search(request.args["query"])]
  except OperationalError:
    return render_template("search.malformed.html", query=request.args["query"])


  # now get all the information about the results
  try:
    results = Tag.select().where(Tag.tag << tags, ~(Tag.type << ["item"]))
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

  # TODO again, is there a JOIN for this? check tag.py for similar issue: maybe put slogans etc. in the tags table?
  for result in complete:
    for extra in extras:
      try:
        setattr(result, extra, extras[extra].get(extras[extra].tag == result.tag).html)
      except extras[extra].DoesNotExist:
        pass
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
                         radius=radius,
                         headings=tag.headings)

