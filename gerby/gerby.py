import os
import re
from flask import Flask, request, session, g, redirect, url_for, abort, render_template

from peewee import *
from playhouse.sqlite_ext import *
import bibtexparser

import gerby.config as config

db = SqliteExtDatabase(config.DATABASE)

# TODO this should be taken from a different package?
# TODO or should the tools and the server be in the same package?
class BaseModel(Model):
  class Meta:
    database = db

class Tag(BaseModel):
  tag = CharField(unique=True, primary_key=True)
  label = CharField(unique=True, null=True)
  active = BooleanField(null=True)
  ref = CharField(null=True)
  type = CharField(null=True)
  html = TextField(null=True)

  # allows us to sort tags according to their reference
  def __gt__(self, other):
    try:
      return tuple(map(int, self.ref.split("."))) > tuple(map(int, other.ref.split(".")))
    except ValueError:
      return 0 # just do something, will need to implement a better version

class TagSearch(FTSModel):
  tag = SearchField()
  html = SearchField() # HTML of the statement or (sub)section
  full = SearchField() # HTML of the statement including the proof (if relevant)

  class Meta:
    database = db

class Proof(BaseModel):
  tag = ForeignKeyField(Tag, related_name = "proofs")
  html = TextField(null=True)
  number = IntegerField()

class Dependency(BaseModel):
  tag = ForeignKeyField(Tag, related_name="from")
  to = ForeignKeyField(Tag, related_name="to")

class Footnote(BaseModel):
  label = CharField(unique=True, primary_key=True)
  html = TextField(null=True)

class Extra(BaseModel):
  tag = ForeignKeyField(Tag)
  html = TextField(null=True)

class LabelName(BaseModel):
  tag = ForeignKeyField(Tag)
  name = CharField()

class BibliographyEntry(BaseModel):
  key = CharField(unique=True, primary_key=True)
  entrytype = CharField()

class Citation(BaseModel):
  tag = ForeignKeyField(Tag)
  key = ForeignKeyField(BibliographyEntry)

class BibliographyField(BaseModel):
  key = ForeignKeyField(BibliographyEntry)
  field = CharField()
  value = CharField()



# Flask setup code
app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
  DATABASE=os.path.join(app.root_path, "stacks.sqlite"),
))

"""
static pages
"""
@app.route("/")
def show_tags():
  return render_template("static/about.html")

@app.route("/about")
def show_about():
  return render_template("static/about.html")

"""
dynamic pages
"""
@app.route("/browse")
def show_chapters():
  chapters = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "chapter")
  chapters = sorted(chapters)

  return render_template("show_chapters.html", chapters=chapters)

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

@app.route("/tag/<string:tag>")
# TODO we also need to support the old format of links!
def show_tag(tag):
  tag = Tag.get(Tag.tag == tag)

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

@app.route("/bibliography")
def show_bibliography():
  entries = BibliographyEntry.select()

  for entry in entries:
    fields = BibliographyField.select().where(BibliographyField.key == entry.key)
    for field in fields:
      setattr(entry, field.field, field.value)

  return render_template("show_bibliography.html", entries=entries)

@app.route("/bibliography/<string:key>")
def show_entry(key):
  entry = BibliographyEntry.get(BibliographyEntry.key == key)

  fields = BibliographyField.select().where(BibliographyField.key == entry.key)
  entry.fields = dict()
  for field in fields:
    entry.fields[field.field] = field.value

  return render_template("show_entry.html", entry=entry)
