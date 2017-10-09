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
      if not hasattr(output[-1], "children"):
        output[-1].children = []

      output[-1].children.append(tag)

  for tag in output:
    if hasattr(tag, "children"):
      combine(tag.children)

  return output

def tree(parent):
  tags = Tag.select(Tag.tag, Tag.ref, Tag.type, Tag.html, LabelName.name).join(LabelName, JOIN_LEFT_OUTER).where(Tag.ref.startswith(parent.ref + "."), Tag.type << headings)
  tags = sorted(tags)

  return combine(tags)


@app.route("/tag/<string:tag>")
# TODO we also need to support the old format of links!
def show_tag(tag):
  tag = Tag.get(Tag.tag == tag)

  if tag.type in headings:
    tree(tag)

  if tag.type == "chapter":
    chapter = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.tag == tag).get()

    sectionCommands = ["section", "subsection", "subsubsection"] # so we assume that the top level is chapter
    # we ignore this for now, and do things by hand...

    def depth(tag):
      return len(tag.ref.split("."))

    tags = Tag.select(Tag.tag, Tag.ref, Tag.type, LabelName.name).join(LabelName, JOIN.LEFT_OUTER).where(Tag.ref.startswith(tag.ref + "."))
    tags = sorted(tags)

    sections = [tag for tag in tags if tag.type == "section"]

    for section in sections:
      section.children = []

      for tag in tags:
        if tag.ref.startswith(section.ref + ".") and depth(tag) == depth(section) + 1:
          section.children.append(tag)

      for child in section.children:
        if child.type == "subsection":
          child.children = []

          for tag in tags:
            if tag.ref.startswith(child.ref) and depth(tag) == depth(child) + 1:
              child.children.append(tag)

    return render_template("show_chapter.html", chapter=chapter, sections=sections)

  else:
    # TODO maybe always generate the breadcrumb data, but only pass it if at least 3 levels deep?
    # we could have a top breadcrumb if 3 levels deep
    # and an "overview where you're at", on the right now, as many levels as necessary?

    # if something is at least 3 levels deep we show a breadcrumb
    breadcrumb = None
    if len(tag.ref.split(".")) > 2:
      parents = [".".join(tag.ref.split(".")[:-1])]
      while parents[-1] != "":
        parents.append(".".join(parents[-1].split(".")[:-1]))

      # TODO can we do a select with join without specifying all the columns?
      breadcrumb = sorted(Tag.select(Tag.tag, Tag.ref, Tag.type, LabelName.name).join(LabelName).where(Tag.ref << parents))

    # if something is a section, we allow people to navigate by section
    sections = None
    if tag.type == "section":
      # TODO just put in an extra column in Tag, with the in-text order of things, to make life easier...
      pass

    proofs = Proof.select().where(Proof.tag == tag.tag)

    # handle footnotes
    """<a class="footnotemark" href="#{{ obj.id }}" id="{{ obj.id }}-mark"><sup>{{ obj.mark.attributes.num }}</sup></a>"""
    pattern = re.compile("class=\"footnotemark\" href=\"#(a[0-9]+)\"")

    html = tag.html + "".join([proof.html for proof in proofs])

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

    return render_template("show_tag.html", tag=tag, breadcrumb=breadcrumb, html=html, footnotes=footnotes)


