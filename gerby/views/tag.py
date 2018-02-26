import datetime

from flask import render_template

from gerby.application import app
from gerby.database import *
from gerby.views.methods import *

import gerby.configuration

import re

headings = ["part", "chapter", "section", "subsection", "subsubsection"]
hideComments = ["part", "chapter"]
extras = {"slogan": Slogan, "history": History, "reference": Reference}

# Tags pattern as used in the tag_up scripts
TAGS_PATTERN = re.compile("^[0-9a-zA-Z]{4}")

# validate whether something is (potentially) a tag
def isTag(string):
  return TAGS_PATTERN.match(string) is not None and len(string) == 4

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

# for the absolutely ancient redirect setup
@app.route("/index.php?page=tag?tag=<string:tag>")
def redirect_to_tag(tag):
  return redirect("/tag/" + tag)


@app.route("/tag/<string:tag>")
@app.route("/tag/tag/<string:tag>")
def show_tag(tag):
  tag = tag.upper()

  if not isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  if not Tag.select().where(Tag.tag == tag).exists():
    return render_template("tag.notfound.html", tag=tag)

  tag = (Tag.select(Tag, Slogan, History,Reference)
              .where(Tag.tag == tag.upper())
              .join(Slogan, JOIN.LEFT_OUTER, on=(Tag.tag == Slogan.tag))
              .join(History, JOIN.LEFT_OUTER, on=(Tag.tag == History.tag))
              .join(Reference, JOIN.LEFT_OUTER, on=(Tag.tag == Reference.tag)))[0]

  html = ""
  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in headings:
    html = tag.html

    # if we are below the cutoff: generate all data below it too
    if headings.index(tag.type) >= headings.index(gerby.configuration.UNIT):
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type << headings)
      html = html + "".join([item.html for item in sorted(tags)])

      # add badges for extras
      pattern = re.compile("id=\"([0-9A-Z]{4})\">")
      identifiers = pattern.findall(html)

      references = Reference.select().where(Reference.tag << identifiers)
      for reference in references:
        html = html.replace("id=\"" + reference.tag.tag + "\">", 'id="' + reference.tag.tag + '"><a tabindex="0" role="button" data-trigger="focus" data-placement="bottom" class="btn badge badge-info" data-toggle="popover" title="Reference" data-html="true" data-content=\'' + reference.html + '\'>reference</a>')
      histories = History.select().where(History.tag << identifiers)
      for history in histories:
        html = html.replace("id=\"" + history.tag.tag + "\">", 'id="' + history.tag.tag + '"><a tabindex="0" role="button" data-trigger="focus" data-placement="bottom" class="btn badge badge-secondary" data-toggle="popover" title="Historical remark" data-html="true" data-content=\'' + history.html + '\'>historical remark</a>')
      slogans = Slogan.select().where(Slogan.tag << identifiers)
      for slogan in slogans:
        html = html.replace("id=\"" + slogan.tag.tag + "\">", 'id="' + slogan.tag.tag + '"><a tabindex="0" role="button" data-trigger="focus" data-placement="bottom" class="btn badge badge-primary" data-toggle="popover" title="Slogan" data-html="true" data-content=\'' + slogan.html + '\'>slogan</a>')


  # it's an item
  elif tag.type == "item":
    html = "<ul>" + tag.html + "</ul>" # <ol start> is incompatible with our current counter setup

  # it's a tag (maybe with proofs)
  else:
    proofs = Proof.select().where(Proof.tag == tag.tag)
    html = tag.html + "".join([proof.html for proof in proofs])

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
  if tag.type in headings and headings.index(tag.type) < headings.index(gerby.configuration.UNIT):
    # if the tag is a part, we select all chapters, and then do the startswith for these
    if tag.type == "part":
      chapters = Part.select(Part.chapter).where(Part.part == tag.tag)
      chapters = Tag.select().where(Tag.tag << [chapter.chapter.tag for chapter in chapters])

      # even this is too slow for the Stacks project
      #tags = [Tag.select().where(Tag.ref.startswith(chapter.ref + "."), Tag.type << ["section"]) for chapter in chapters] # only consider sections
      #tags = list(chapters) + [tag for sublist in tags for tag in sublist] # flatten

      # so we just do this
      tags = list(chapters)
    else:
      tags = (Tag.select(Tag.tag,
                        Tag.label,
                        Tag.active,
                        Tag.ref,
                        Tag.type,
                        Tag.html,
                        Tag.name,
                        Reference.html.alias("reference"),
                        History.html.alias("history"),
                        Slogan.html.alias("slogan"))
                .join(Reference, JOIN.LEFT_OUTER, on=(Tag.tag == Reference.tag))
                .join(History, JOIN.LEFT_OUTER, on=(Tag.tag == History.tag))
                .join(Slogan, JOIN.LEFT_OUTER, on=(Tag.tag == Slogan.tag))
                .where(Tag.ref.startswith(tag.ref + ".")))

    tree = combine(sorted(tags))

  # dealing with comments
  commentsEnabled = tag.type not in hideComments and Comment.table_exists()
  comments = []
  parentComments = []
  if commentsEnabled:
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
                         commentsEnabled=commentsEnabled,
                         comments=comments,
                         filename=tag.label.split("-" + tag.type)[0],
                         parentComments=parentComments,
                         depth=gerby.configuration.DEPTH)

@app.route("/tag/<string:tag>/cite")
def show_citation(tag):
  if not isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  try:
    tag = Tag.get(Tag.tag == tag.upper())
  except Tag.DoesNotExist:
    return render_template("tag.notfound.html", tag=tag)

  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  return render_template("tag.citation.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         time=datetime.datetime.utcnow())

@app.route("/tag/<string:tag>/statistics")
def show_tag_statistics(tag):
  if not isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  try:
    tag = Tag.get(Tag.tag == tag.upper())
  except Tag.DoesNotExist:
    return render_template("tag.notfound.html", tag=tag)

  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  dependencies = sorted(Dependency.select().where(Dependency.to == tag.tag))

  for dependency in dependencies:
    ref = ".".join(dependency.tag.ref.split(".")[0:-1])
    dependency.parent = Tag.select().where(Tag.ref == ref, ~(Tag.type << ["item"])).get()

  statistics = dict()
  if TagStatistic.table_exists():
    for statistic in ["preliminaries", "chapters", "sections", "consequences"]:
      try:
        statistics[statistic] = TagStatistic.get(TagStatistic.tag == tag, TagStatistic.statistic == statistic).value
      except TagStatistic.DoesNotExist:
        log.warning("Unable to get statistic '{0}' for tag '{1}'.".format(statistic, tag))
        statistics[statistic] = -1

  return render_template("tag.statistics.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         statistics=statistics,
                         filename=tag.label.split("-" + tag.type)[0],
                         dependencies = dependencies)
