import os, os.path, time
import urllib.request
import feedparser
import re
from flask import Flask, render_template, request, send_from_directory
import flask_profiler

from peewee import *
from playhouse.sqlite_ext import *

from gerby.configuration import *
from gerby.database import *

db.init(DATABASE)

# Flask setup code
app = Flask(__name__)
app.config.from_object(__name__)

app.config["flask_profiler"] = {
    "enabled": "true",
    "storage": {
        "engine": "sqlite"
    },
    "basicAuth":{
        "enabled": False,
    },
    "ignore": [
	    "^/static/.*"
	]
}


feeds = {
  "github": {
    "url": "https://github.com/stacks/stacks-project/commits/master.atom",
    "title": "Recent commits",
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

  statistics.append(str(BookStatistic.get(BookStatistic.statistic == "lines").value) + " lines of code")

  tags = Tag.select().where(Tag.active == True).count()
  statistics.append(str(tags) + " tags")

  statistics.append(str(Tag.select().where(Tag.type == "section").count()) + " sections")
  statistics.append(str(Tag.select().where(Tag.type == "chapter").count()) + " chapters")

  statistics.append(str(BookStatistic.get(BookStatistic.statistic == "pages").value) + " pages")

  statistics.append(str(Slogan.select().count()) + " slogans")

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
def show_index():
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

  comments = Comment.select().order_by(Comment.id.desc()).paginate(1, 5)

  # TODO make this a pretty JOIN across databases if possible
  for comment in comments:
    comment.tag = Tag.get(Tag.tag == comment.tag)

  return render_template(
      "index.html",
      updates=updates,
      statistics=get_statistics(),
      comments=comments,
      )

@app.route("/about")
def show_about():
  return render_template("single/about.html")

@app.route("/statistics")
def show_statistics():
  counts = dict()
  for count in Tag.select(Tag.type, fn.COUNT(Tag.tag).alias("count")).group_by(Tag.type):
    counts[count.type] = count.count

  records = dict()
  records["complex"] = TagStatistic.select(TagStatistic.tag, fn.MAX(TagStatistic.value).alias("value")).where(TagStatistic.statistic == "preliminaries").execute()[0]
  records["used"] = TagStatistic.select(TagStatistic.tag, fn.MAX(TagStatistic.value).alias("value")).where(TagStatistic.statistic == "consequences").execute()[0]

  #records["complex"] = Tag.get(Tag.tag == TagStatistic.get(TagStatistic.type == "preliminaries", TagStatistic.value == fn.Max(TagStatistic.).tag)
  return render_template("single/statistics.html", counts=counts, records=records)

@app.route("/browse")
def show_chapters():
  # part is top-level
  if Tag.select().where(Tag.type == "part").exists():
    chapters = Part.select()
    parts = Tag.select().join(Part, on=Part.part).order_by(Tag.ref).distinct()

    for part in parts:
      part.chapters = sorted([chapter.chapter for chapter in chapters if chapter.part.tag == part.tag])

    return render_template("toc.parts.html", parts=parts)

  # chapter is top-level
  else:
    chapters = Tag.select().where(Tag.type == "chapter")
    chapters = sorted(chapters)

    return render_template("toc.chapters.html", chapters=chapters)


@app.route("/robots.txt")
def show_robots():
  return send_from_directory(app.static_folder, request.path[1:])

app.jinja_env.add_extension('jinja2.ext.do')

import gerby.views.bibliography
import gerby.views.comments
import gerby.views.search
import gerby.views.tag


flask_profiler.init_app(app)
# Stacks project specific pages
import gerby.views.stacks

