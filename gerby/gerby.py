import os
import json
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template
from flask.ext.jsonpify import jsonify
import time

from peewee import *
from playhouse.sqlite_ext import *
from playhouse.shortcuts import model_to_dict

FILENAME = "stacks.sqlite"

db = SqliteExtDatabase(FILENAME)

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
    return tuple(map(int, self.ref.split("."))) > tuple(map(int, other.ref.split(".")))

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

class Extra(BaseModel):
  tag = ForeignKeyField(Tag)
  html = TextField(null=True)

class LabelName(BaseModel):
  tag = ForeignKeyField(Tag)
  name = CharField()


# Flask setup code
app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
  DATABASE=os.path.join(app.root_path, "stacks.sqlite"),
))

def all_tags():
  return Tag.select()

@app.route("/")
def show_tags():
  return render_template("show_tags.html", tags=all_tags())

@app.route("/api/")
def api_show_tags():
  tags = all_tags()
  return jsonify({"tags": [model_to_dict(t) for t in tags]})

def tag_data(tag):
  tag = Tag.get(Tag.tag == tag)

  if tag.type == "chapter":
    sections = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "section", Tag.ref.startswith(tag.ref + "."))
    sections = sorted(sections)

    # to avoid n+1 query we select all tags at once and then let Python figure it out
    tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type != "section")
    tags = sorted(tags)
    for section in sections:
      section.tags = [tag for tag in tags if tag.ref.startswith(section.ref + ".")]

    return tag, {"chapter": tag, "sections": sections}

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

    return tag, {"tag": tag, "breadcrumb": breadcrumb, "proofs": proofs}


@app.route("/tag/<string:tag>")
def show_tag(tag):
  tag, data = tag_data(tag)
  if tag.type == "chapter":
    return render_template("show_chapter.html", chapter=data["chapter"], sections=data["sections"])
  else:
    return render_template("show_tag.html", tag=data["tag"], breadcrumb=data["breadcrumb"], proofs=data["proofs"])

@app.route("/api/tag/<string:tag>")
def api_show_tag(tag):
  tag, data = tag_data(tag)
  if tag.type == "chapter":
    return jsonify({"type": "chapter", "chapter": model_to_dict(data["chapter"]), "sections": [model_to_dict(s) for s in data["sections"]]})
  else:
    bcrumb = [model_to_dict(d) for d in data["breadcrumb"]] if data["breadcrumb"] is not None else []
    return jsonify({"type": "tag", "tag": model_to_dict(data["tag"]), 
                     "breadcrumb": bcrumb,
                     "proofs": [model_to_dict(p) for p in data["proofs"]]})

def get_chapters():
  chapters = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "chapter")
  return sorted(chapters)


@app.route("/browse")
def show_chapters():
  return render_template("show_chapters.html", chapters=get_chapters())


@app.route("/api/browse")
def api_show_chapters():
  chapters = get_chapters()
  return jsonify({"chapters": [model_to_dict(c) for c in chapters]})

# THESE ARE STUBS
def get_search():
  # TODO not sure whether this is an efficient query: only fulltext and docid is quick apparently
  # TODO can we use TagSearch.docid and Tag.rowid or something?
  # TODO can we match on a single column? maybe we need two tables?
  query = "Eilenberg"
  results = Tag.select(Tag, TagSearch, TagSearch.rank().alias("score")).join(TagSearch, on=(Tag.tag == TagSearch.tag).alias("search")).where(TagSearch.match(query), Tag.type.not_in(["chapter", "section", "subsection"]))
  return results

@app.route("/search")
def show_search():
  results = get_search()
  return render_template("show_search.html", results=results)

@app.route("/api/search")
def api_show_search():
  results = get_search()
  return jsonify({"results": [model_to_dict(r) for r in results]})