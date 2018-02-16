import hashlib

from flask import render_template, send_from_directory, redirect
from datetime import datetime

from gerby.application import app
from gerby.database import *
from gerby.views.methods import *
import gerby.views.tag

# we need this for building GitHub URLs pointing to diffs
@app.context_processor
def md5_processor():
  def md5(string):
    m = hashlib.md5()
    m.update(string.encode("utf-8"))
    return m.hexdigest()

  return dict(md5=md5)


@app.route("/tags")
def show_tags():
  return render_template("single/tags.html")


@app.route("/todo")
def show_todo():
  return render_template("single/todo.html")


@app.route("/markdown")
def show_markdown():
  return render_template("single/markdown.html")


@app.route("/acknowledgements")
def show_acknowledgements():
  acknowledgements = []

  with open("tex/documentation/support") as f:
    for line in f:
      if line.startswith("%") or line.isspace():
        continue
      acknowledgements.append(line)

  return render_template("single/acknowledgements.html", acknowledgements=acknowledgements)


@app.route("/contribute")
def show_contribute():
  return render_template("single/contribute.html")


@app.route("/contributors")
def show_contributors():
  contributors = []

  with open("tex/CONTRIBUTORS") as f:
    for line in f:
      if line.startswith("%") or line.isspace():
        continue
      contributors.append(line)

  return render_template("single/contributors.html", contributors=contributors)


@app.route("/api")
def show_api():
  return render_template("single/api.html")


@app.route("/data/tag/<string:tag>/content/statement")
def show_api_statement(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  html = tag.html

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in gerby.views.tag.headings:
    # if we are below the cutoff: generate all data below it too
    if gerby.views.tag.headings.index(tag.type) >= gerby.views.tag.headings.index(config.UNIT):
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type << gerby.views.tag.headings)
      html = html + "".join([item.html for item in sorted(tags)])

  return html


@app.route("/data/tag/<string:tag>/content/full")
def show_api_tag(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  # if the tag is section-like: decide whether we output a table of contents or generate all output
  # the second case is just like an ordinary tag, but with tags glued together, and is treated as such
  if tag.type in gerby.views.tag.headings:
    html = tag.html

    # if we are below the cutoff: generate all data below it too
    if gerby.views.tag.headings.index(tag.type) >= gerby.views.tag.headings.index(config.UNIT):
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type << gerby.views.tag.headings)
      html = html + "".join([item.html for item in sorted(tags)])

  # it's a tag (maybe with proofs)
  else:
    proofs = Proof.select().where(Proof.tag == tag.tag)
    html = tag.html + "".join([proof.html for proof in proofs])

  return html


@app.route("/tag/<string:tag>/history")
def show_history(tag):
  if not gerby.views.tag.isTag(tag):
    return render_template("tag.invalid.html", tag=tag)

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return render_template("tag.notfound.html", tag=tag)

  breadcrumb = gerby.views.tag.getBreadcrumb(tag)
  neighbours = gerby.views.tag.getNeighbours(tag)

  # only show history for tags for which we have one
  if tag.type not in ["definition", "example", "exercise", "lemma", "proposition", "remark", "remarks", "situation", "theorem"]:
    return render_template("tag.history.invalid.html", tag=tag, breadcrumb=breadcrumb)

  changes = Change.select().join(Commit).where(Change.tag == tag).order_by(Commit.time.desc())
  for change in changes:
    change.commit.time = change.commit.time.decode("utf-8").split(" ")[0] # why in heaven's name is this returning bytes?!

  # this means something went wrong
  if len(changes) == 0:
    return render_template("tag.history.empty.html", tag=tag, breadcrumb=breadcrumb)

  return render_template("tag.history.html",
                         tag=tag,
                         changes=changes,
                         breadcrumb=breadcrumb,
                         neighbours=neighbours)


@app.route("/chapter/<int:chapter>")
def show_chapter_message(chapter):
  try:
    tag = Tag.get(Tag.type == "chapter", Tag.ref == chapter)

    return render_template("tag.chapter.redirect.html", tag=tag)
  except DoesNotExist:
    return render_template("tag.chapter.notfound.html", chapter=chapter)


@app.route("/tex")
@app.route("/tex/<string:filename>")
def send_to_github(filename=""):
  if filename != "":
    return redirect("https://github.com/stacks/stacks-project/blob/master/%s" % filename)
  else:
    return redirect("https://github.com/stacks/stacks-project")


@app.route("/download/<string:filename>")
def download_pdf(filename):
  return send_from_directory("tex/tags/tmp", filename)


@app.route("/recent-changes")
def show_recent_changes():
  commits = Commit.select().order_by(Commit.time.desc()).limit(10)
  for commit in commits:
    commit.time = datetime.datetime.strptime(commit.time.decode(), "%Y-%m-%d %H:%M:%S %z")
    commit.tags = sorted(Tag.select().join(Change).where(Change.commit == commit, Change.action << ["tag", "statement", "proof", "statement and proof"]).distinct())

  return render_template("stacks/changes.html", commits=commits)

