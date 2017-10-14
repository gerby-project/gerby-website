from flask import render_template

from gerby.gerby import app
from gerby.database import *

headings = ["chapter", "section", "subsection", "subsubsection"]

# turn a flat list into a tree based on tag.ref length
def combine(tags):
  level = min([len(tag.ref.split(".")) for tag in tags], default=0)

  output = []
  for tag in tags:
    if len(tag.ref.split(".")) == level:
      output.append(tag)
    else:
      # consider "theorem 3.2.0.1": it should go with 3.2, not the non-existent 3.2.0
      if len(output) == 0:
        output.append(tag)
      # just normal structure here
      else:
        if not hasattr(output[-1], "children"):
          output[-1].children = []
        output[-1].children.append(tag)

  for tag in output:
    if hasattr(tag, "children"):
      tag.children = combine(tag.children)

  return output

def getBreadcrumb(tag):
  pieces = tag.ref.split(".")
  output = []
  refs = [".".join(pieces[0:i]) for i in range(len(pieces))]

  # one has to pay attention to numbered lists
  tags = Tag.select(Tag.tag, Tag.ref, Tag.type, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref << refs, Tag.type << headings)

  return sorted(tags)

@app.route("/tag/<string:tag>")
# TODO we also need to support the old format of links!
def show_tag(tag):
  tag = Tag.get(Tag.tag == tag)

  html = ""
  breadcrumb = getBreadcrumb(tag)

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in headings:
    tags = Tag.select(Tag.tag, Tag.ref, Tag.type, Tag.html, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref.startswith(tag.ref + "."))
    tags = sorted(tags)

    # if we are below the cutoff: generate all data
    html = tag.html
    if headings.index(tag.type) > headings.index(config.UNIT):
      html = html + "".join([item.html for item in tags])

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

  # if it's a heading
  if tag.type in headings and headings.index(tag.type) < headings.index(config.UNIT):
    tree = combine(tags)

    return render_template("show_tag.html",
                           tag=tag,
                           breadcrumb=breadcrumb,
                           html=html,
                           footnotes=footnotes,
                           tree=tree)
  else:
    return render_template("show_tag.html",
                           tag=tag,
                           breadcrumb=breadcrumb,
                           html=html,
                           footnotes=footnotes)
