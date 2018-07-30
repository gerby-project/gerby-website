import os
import os.path
import time
import urllib.request
import socket
import feedparser
import re
from flask import Flask, render_template, request, send_from_directory
#import flask_profiler

from peewee import *
from playhouse.sqlite_ext import *

from gerby.configuration import *
from gerby.database import *

db.init(DATABASE)

# Flask setup code
app = Flask(__name__)
app.config.from_object(__name__)

#app.config["flask_profiler"] = {
#    "enabled": "true",
#    "storage": {
#        "engine": "sqlite"
#    },
#    "basicAuth": {
#        "enabled": False,
#    },
#    "ignore": ["^/static/.*"]
#}

feeds = {
  "github": {
    "url": "https://github.com/stacks/stacks-project/commits/master.atom",
    "title": "Recent commits",
    "link": "https://github.com/stacks/stacks-project/commits",
  },
  "blog": {
    "url": "https://www.math.columbia.edu/~dejong/wordpress/?feed=rss2",
    "title": "Recent blog posts",
    "link": "https://www.math.columbia.edu/~dejong/wordpress",
  },
}

# set timeout for feed request
socket.setdefaulttimeout(5)


def get_statistics():
  statistics = []

  if BookStatistic.table_exists():
    try:
      statistics.append(str(BookStatistic.get(BookStatistic.statistic == "pages").value) + " pages")
    except BookStatistic.DoesNotExist:
      app.logger.warning("No entry 'pages' in table 'BookStatistics'.")

    try:
      statistics.append(str(BookStatistic.get(BookStatistic.statistic == "lines").value) + " lines of code")
    except BookStatistic.DoesNotExist:
      app.logger.warning("No entry 'lines' in table 'BookStatistics'.")

  tags = Tag.select().where(Tag.active == True).count()
  statistics.append(str(tags) + " tags")
  statistics.append(str(Tag.select().where(Tag.type == "section").count()) + " sections")
  statistics.append(str(Tag.select().where(Tag.type == "chapter").count()) + " chapters")
  statistics.append(str(Slogan.select().count()) + " slogans")

  return statistics

feedsDirectory = app.instance_path + "/feeds"

def update_feeds():
  # make sure there is a directory
  if not os.path.exists(feedsDirectory):
    os.makedirs(feedsDirectory)

  # update if needed (i.e. older than 1 hour)
  for label, feed in feeds.items():
    path = feedsDirectory + "/" + label + ".feed"
    if not os.path.isfile(path) or time.time() - os.path.getmtime(path) > 3600:
      try:
        urllib.request.urlretrieve(feed["url"], path)
      except:
        # when this happens we should probably add more information etc. but for now it's just caught
        app.logger.warning("feed '%s' did not load properly" % feed["title"])


@app.route("/")
def show_index():
  update_feeds()

  updates = []
  for label, feed in feeds.items():
    update = {"title": "<a href='" + feed["link"] + "'>" + feed["title"] + "</a>", "entries": []}

    d = feedparser.parse(feedsDirectory + "/" + label + ".feed")
    for i in range(min(5, len(d.entries))):
      entry = "<span class='date'>" + time.strftime("%d %b %Y", d.entries[i].updated_parsed) + "</span>: "
      entry = entry + "<a href='" + d.entries[i].link + "'>" + d.entries[i].title + "</a>"
      update["entries"].append(entry)

    updates.append(update)

  comments = []
  if Comment.table_exists():
    comments = Comment.select().where(Comment.active).order_by(Comment.id.desc()).paginate(1, 5)

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
  total = Tag.select().count()

  counts = dict()
  for count in Tag.select(Tag.type, fn.COUNT(Tag.tag).alias("count")).group_by(Tag.type):
    counts[count.type] = count.count

  extras = dict()
  for (name, extra) in {"slogans": Slogan, "references": Reference, "historical remarks": History}.items():
    extras[name] = extra.select().count()
  extras["comments"] = Comment.select().where(Comment.active).count()

  records = dict()
  records["complex"] = TagStatistic.select(TagStatistic.tag, fn.MAX(TagStatistic.value).alias("value")).where(TagStatistic.statistic == "preliminaries").execute()[0]
  records["used"] = TagStatistic.select(TagStatistic.tag, fn.MAX(TagStatistic.value).alias("value")).where(TagStatistic.statistic == "consequences").execute()[0]
  records["referenced"] = Dependency.select(Dependency.to, fn.COUNT(Dependency.to).alias("value")).group_by(Dependency.to).order_by(fn.COUNT(Dependency.to).desc())[0]
  records["proof"] = Proof.select(Proof.tag, fn.length(Proof.html).alias("value")).order_by(fn.length(Proof.html).desc())[0]

  return render_template("single/statistics.html", total=total, counts=counts, extras=extras, records=records)


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


#flask_profiler.init_app(app)

# Stacks project specific pages
import gerby.views.stacks
