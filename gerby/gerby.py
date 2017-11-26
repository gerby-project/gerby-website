import os, os.path, time
import urllib.request
import feedparser
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

feeds = {
  "github": {
    "url": "https://github.com/stacks/stacks-project/commits/master.atom",
    "title": "Recent changes",
    "link": "https://github.com/stacks/stacks-project/commits",
  },
  "blog": {
    "url": "http://math.columbia.edu/~dejong/wordpress/?feed=rss2",
    "title": "Recent blog posts",
    "link": "http://math.columbia.edu/~dejong/wordpress",
  },
}

def get_statistics():
  statistics = []

  tags = Tag.select().count()
  inactive = Tag.select().where(Tag.active == False).count()
  statistics.append(str(tags) + " tags (" + str(inactive) + " inactive)")

  statistics.append(str(Tag.select().where(Tag.type == "section").count()) + " sections")
  statistics.append(str(Tag.select().where(Tag.type == "chapter").count()) + " chapters")

  # TODO more statistics

  return statistics

def update_feeds():
  # make sure there is a directory
  if not os.path.exists("feeds"):
    os.makedirs("feeds")

  # update if needed
  for label, feed in feeds.items():
    path = "feeds/" + label + ".feed"
    if not os.path.isfile(path) or time.time() - os.path.getmtime(path) > 3600:
      urllib.request.urlretrieve(feed["url"], path)

@app.route("/")
def show_tags():
  update_feeds()

  updates = []
  for label, feed in feeds.items():
    update = {"title": "<a href='" + feed["link"] + "'>" + feed["title"] + "</a>", "entries": []}

    d = feedparser.parse("feeds/" + label + ".feed")
    for i in range(min(5, len(d.entries))):
      entry = "<span class='date'>" + time.strftime("%d %b %Y", d.entries[i].updated_parsed) + "</span>: "
      entry = entry + "<a href='" + d.entries[i].link + "'>" + d.entries[i].title + "</a>"
      update["entries"].append(entry)

    updates.append(update)

  # TODO add recent comments here

  return render_template("index.html", updates=updates, statistics=get_statistics())

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

