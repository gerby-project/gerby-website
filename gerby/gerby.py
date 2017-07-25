import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template
import time

from peewee import *

FILENAME = "stacks.sqlite"

db = SqliteDatabase(FILENAME)

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

@app.route("/")
def show_tags():
  tags = Tag.select()

  return render_template("show_tags.html", tags=tags)

@app.route("/tag/<string:tag>")
def show_tag(tag):
  tag = Tag.get(Tag.tag == tag)

  if tag.type == "chapter":
    sections = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "section", Tag.ref.startswith(tag.ref + "."))
    sections = sorted(sections)

    # to avoid n+1 query we select all tags at once and then let Python figure it out
    tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type != "section")
    tags = sorted(tags)
    for section in sections:
      section.tags = [tag for tag in tags if tag.ref.startswith(section.ref + ".")]

    return render_template("show_chapter.html", chapter=tag, sections=sections)

  else:
    return render_template("show_tag.html", tag=tag)

@app.route("/browse")
def show_chapters():
  chapters = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "chapter")
  chapters = sorted(chapters)

  return render_template("show_chapters.html", chapters=chapters)
