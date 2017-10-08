import os
import re
from flask import Flask, render_template

from peewee import *
from playhouse.sqlite_ext import *

import gerby.config as config
from gerby.database import *

db = SqliteExtDatabase(config.DATABASE)

# Flask setup code
app = Flask(__name__)
app.config.from_object(__name__)

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


import gerby.views.bibliography
import gerby.views.search
import gerby.views.tag
