from flask import render_template

from gerby.gerby import app
from gerby.database import *

headings = ["chapter", "section", "subsection", "subsubsection"]

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

def getBreadcrumb(tag):
  pieces = tag.ref.split(".")
  output = []
  refs = [".".join(pieces[0:i]) for i in range(len(pieces) + 1)]

  tags = Tag.select(Tag.tag, Tag.ref, Tag.type, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref << refs, ~(Tag.type << ["item"]))

  return sorted(tags)

def getNeighbours(tag):
  pieces = tag.ref.split(".")
  try:
    pieces[-1] = int(pieces[-1])
  except ValueError:
    return (None, None) # TODO deal with appendices

  # left
  pieces[-1] = pieces[-1] - 1
  left = ".".join(map(str, pieces))
  try:
    left = Tag.get(Tag.ref == left)
  except Tag.DoesNotExist:
    left = None

  # right
  pieces[-1] = pieces[-1] + 2
  right = ".".join(map(str, pieces))
  try:
    right = Tag.get(Tag.ref == right)
  except Tag.DoesNotExist:
    right = None

  return (left, right)

@app.route("/tag/<string:tag>")
# TODO we also need to support the old format of links!
def show_tag(tag):
  tag = Tag.get(Tag.tag == tag)

  html = ""
  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in headings:
    html = tag.html

    # if we are below the cutoff: generate all data below it too
    if headings.index(tag.type) >= headings.index(config.UNIT):
      tags = Tag.select(Tag.tag, Tag.ref, Tag.type, Tag.html, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref.startswith(tag.ref + "."), Tag.type << headings)
      html = html + "".join([item.html for item in sorted(tags)])

  # it's a tag (maybe with proofs)
  else:
    proofs = Proof.select().where(Proof.tag == tag.tag)
    html = tag.html + "".join([proof.html for proof in proofs])


  # handle footnotes
  #<a class="footnotemark" href="#{{ obj.id }}" id="{{ obj.id }}-mark"><sup>{{ obj.mark.attributes.num }}</sup></a>
  pattern = re.compile("class=\"footnotemark\" href=\"#(a[0-9]+)\"")

  labels = pattern.findall(html)
  for number, label in enumerate(labels):
    # TODO this is not how regexes should be used... (if you need test material when fixing this, see tag 05QM)
    old = re.search(r"id=\"" + label + "-mark\"><sup>([0-9]+)</sup>", html).group(1)
    html = html.replace(
        "id=\"" + label + "-mark\"><sup>" + old + "</sup>",
        "id=\"" + label + "-mark\"><sup>" + str(number + 1) + "</sup>")
    # make the HTML pretty (and hide plasTeX id's)
    html = html.replace(label, "footnote-" + str(number + 1))

  footnotes = Footnote.select().where(Footnote.label << labels)

  tree = None
  # if it's a heading
  if tag.type in headings and headings.index(tag.type) < headings.index(config.UNIT):
    tags = Tag.select(Tag.tag, Tag.ref, Tag.type, Tag.html, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref.startswith(tag.ref + "."))
    tree = combine(sorted(tags))

  return render_template("show_tag.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours,
                         html=html,
                         footnotes=footnotes,
                         tree=tree)

@app.route("/tag/<string:tag>/cite")
def show_citation(tag):
  tag = Tag.get(Tag.tag == tag)

  breadcrumb = getBreadcrumb(tag)
  neighbours = getNeighbours(tag)

  return render_template("citation.html",
                         tag=tag,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours)
