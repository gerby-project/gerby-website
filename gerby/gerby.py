import os, os.path, time
import urllib.request
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

def update_feeds():
  feeds = {
      "blog": "http://math.columbia.edu/~dejong/wordpress/?feed=rss2",
      "github": "https://github.com/stacks/stacks-project/commits/master.atom",
    }

  # make sure there is a directory
  if not os.path.exists("feeds"):
    os.makedirs("feeds")

  # update if needed
  for feed in feeds:
    path = "feeds/" + feed + ".feed"
    if not os.path.isfile(path) or time.time() - os.path.getmtime(path) > 3600:
      urllib.request.urlretrieve(feeds[feed], path)

@app.route("/")
def show_tags():
  update_feeds()

  return render_template("index.html")

@app.route("/about")
def show_about():
  return render_template("static/about.html")

@app.route("/browse")
def show_chapters():
  chapters = Tag.select(Tag.tag, Tag.ref, LabelName.name).join(LabelName).where(Tag.type == "chapter")
  chapters = sorted(chapters)

  return render_template("show_chapters.html", chapters=chapters)

app.jinja_env.add_extension('jinja2.ext.do')

import gerby.views.bibliography
import gerby.views.search
import gerby.views.tag

