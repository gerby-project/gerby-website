import datetime

from flask import render_template

from gerby.gerby import app
from gerby.database import *
from gerby.views.methods import *

headings = ["part", "chapter", "section", "subsection", "subsubsection"]
hideComments = ["part", "chapter"]

# validate whether something is (potentially) a tag
def isTag(string):
  return len(string) == 4 # TODO make this more intelligent

# turn a flat list into a tree based on tag.ref length
def combine(tags):
  level = min([len(tag.ref.split(".")) for tag in tags], default=0)

  output = []
  children = []
  for tag in tags:
    # if we are at the bottom level (locally) we add it to the output
    if len(tag.ref.split(".")) == level:
      output.append(tag)
    # if we have a 0 at on the position of the current level we also add it to the output
    elif tag.ref.split(".")[level - 1] == "0":
      output.append(tag)
    else:
      children.append(tag)

  # attach children to the correct parent
  for tag in children:
    # construct the reference for the parent
    ref = ".".join([piece for piece in tag.ref.split(".")[0:level]])
    for parent in output:
      if parent.ref == ref:
        # create children if necessary
        if not hasattr(parent, "children"):
          parent.children = []
        parent.children.append(tag)

  # recurse for all elements in output which have children
  for tag in output:
    if hasattr(tag, "children"):
      tag.children = combine(tag.children)

  return output

def getNeighbours(tag):
  # items cannot be dealt with appropriately, so we just don't
  if tag.type == "item":
    return (None, None)

  pieces = tag.ref.split(".")
  try:
    pieces[-1] = int(pieces[-1])
  except ValueError:
    return (None, None) # TODO deal with appendices

  # left
  pieces[-1] = pieces[-1] - 1
  left = ".".join(map(str, pieces))
  try:
    if tag.type in headings:
      left = Tag.get(Tag.ref == left, Tag.type == tag.type) # to deal with parts appropriately we select for part / chapter with the appropriate number
    else:
      left = Tag.get(Tag.ref == left, Tag.type != "item")
  except Tag.DoesNotExist:
    left = None

  # right
  pieces[-1] = pieces[-1] + 2
  right = ".".join(map(str, pieces))
  try:
    if tag.type in headings:
      right = Tag.get(Tag.ref == right, Tag.type == tag.type) # to deal with parts appropriately we select for part / chapter with the appropriate number
    else:
      right = Tag.get(Tag.ref == right, Tag.type != "item")
  except Tag.DoesNotExist:
    right = None

  return (left, right)

@app.route("/tag/<string:tag>")
# TODO we also need to support the old format of links!
def show_tag(tag):
  if not isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return render_template("tag.notfound.html", tag=tag)

  html = ""
  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in headings:
    html = tag.html

    # if we are below the cutoff: generate all data below it too
    if headings.index(tag.type) >= headings.index(config.UNIT):
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type << headings)
      html = html + "".join([item.html for item in sorted(tags)])

  # it's an item
  elif tag.type == "item":
    html = "<ul>" + tag.html + "</ul>" # <ol start> is incompatible with our current counter setup

  # it's a tag (maybe with proofs)
  else:
    proofs = Proof.select().where(Proof.tag == tag.tag)
    html = tag.html + "".join([proof.html for proof in proofs])

  # TODO fix for SAG because plasTeX cannot do it easily?
  html = html.replace("xymatrix@ 1", "xymatrix@1")

  # TODO remove these! tips for Jacob
  html = html.replace("bigplus", "bigoplus")
  html = html.replace("widecheck", "widehat")
  html = html.replace("degree", "circ") # also, there is an extra close bracket on page 2006, line -4
  html = html.replace("mapsfrom", "mapsto")
  # never use \bf in mathmode, use \mathbf, for all families of fonts
  # don't put things on the right of arrows: quavo (and others)

  # put a space in DAG8S2SS5 for some reason?!
  html = html.replace("\\xymatrix@1{", "\\xymatrix@1{ ")


  # handle footnotes: relabeling the labels to actual numbers
  pattern = re.compile("class=\"footnotemark\" href=\"#(a[0-9]+)\"")
  labels = pattern.findall(html)
  for number, label in enumerate(labels):
    old = re.search(r"id=\"" + label + "-mark\"><sup>([0-9]+)</sup>", html).group(1)
    html = html.replace(
        "id=\"" + label + "-mark\"><sup>" + old + "</sup>",
        "id=\"" + label + "-mark\"></a><a href=\"#" + label + "\"><sup>" + str(number + 1) + "</sup>")
    # make the HTML pretty (and hide plasTeX id's)
    html = html.replace(label, "footnote-" + str(number + 1))

  # adding offset on the footnote marks in the text
  html = html.replace("class=\"footnotemark\"", "class=\"footnotemark footnote-offset\"")

  footnotes = Footnote.select().where(Footnote.label << labels)

  tree = None
  # if it's a heading
  if tag.type in headings and headings.index(tag.type) < headings.index(config.UNIT):
    # if the tag is a part, we select all chapters, and then do the startswith for these
    if tag.type == "part":
      chapters = Part.select(Part.chapter).where(Part.part == tag)
      chapters = Tag.select().where(Tag.tag << [chapter.chapter.tag for chapter in chapters])

      # even this is too slow for the Stacks project
      #tags = [Tag.select().where(Tag.ref.startswith(chapter.ref + "."), Tag.type << ["section"]) for chapter in chapters] # only consider sections
      #tags = list(chapters) + [tag for sublist in tags for tag in sublist] # flatten

      # so we just do this
      tags = list(chapters)
    else:
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."))

      # TODO shouldn't there be a JOIN for this?!
      # TODO in any case, get rid of the copy paste
      for tag in tags:
        try:
          tag.slogan = Slogan.get(Slogan.tag == tag)
        except Slogan.DoesNotExist:
          tag.slogan = None

      for tag in tags:
        try:
          tag.history = History.get(History.tag == tag)
        except History.DoesNotExist:
          tag.history = None

      for tag in tags:
        try:
          tag.reference = Reference.get(Reference.tag == tag)
        except Reference.DoesNotExist:
          tag.reference = None

    tree = combine(sorted(tags))

  # dealing with slogans etc.
  #extras = Extra.select().where(Extra.tag == tag)
  #extras = {extra.type: extra.html for extra in extras}

  # dealing with comments
  comments = Comment.select().where(Comment.tag == tag.tag)
  for comment in comments:
    comment.comment = sfm(comment.comment)

  # looking for comments higher up in the breadcrumb
  parentComments = []
  for parent in breadcrumb:
    if parent.tag == tag.tag:
      continue
    count = Comment.select().where(Comment.tag == parent.tag).count() # this could be done in a single JOIN
    if count > 0:
      parentComments.append([parent, count])

  return render_template("tag.show.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         html=html,
                         footnotes=footnotes,
                         dependencies=Dependency.select().where(Dependency.to == tag.tag),
                         tree=tree,
                         commentsEnabled=tag.type not in hideComments,
                         comments=comments,
                         filename=tag.label.split("-" + tag.type)[0],
                         parentComments=parentComments,
                         depth=config.DEPTH)

@app.route("/tag/<string:tag>/cite")
def show_citation(tag):
  tag = Tag.get(Tag.tag == tag)

  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  return render_template("tag.citation.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         time=datetime.datetime.utcnow())

@app.route("/tag/<string:tag>/statistics")
def show_statistics(tag):
  if not isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return render_template("tag.notfound.html", tag=tag)

  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  dependencies = sorted(Dependency.select().where(Dependency.to == tag.tag))

  for dependency in dependencies:
    ref = ".".join(dependency.tag.ref.split(".")[0:-1])
    dependency.parent = Tag.select().where(Tag.ref == ref, ~(Tag.type << ["item"])).get()

  return render_template("tag.statistics.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         dependencies = dependencies)
