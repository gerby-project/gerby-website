from flask import redirect, render_template, request, redirect

from gerby.application import app
from gerby.database import *
from gerby.views.methods import *

import validators

@app.route("/post-comment", methods=["POST"])
def post_comment():
  tag = request.headers["Referer"].split("/")[-1]

  if tag == request.form["tag"] and tag == request.form["check"]:
    if not validators.email(request.form["mail"]):
      return render_template("comment.invalid-email.html", email=request.form["mail"])

    site = request.form["site"]
    # if site is not a valid url just leave empty
    if not validators.url(request.form["site"]):
      site = ""

    comment = Comment.create(
        tag=request.form["tag"],
        author=request.form["name"],
        site=site,
        email=request.form["mail"],
        comment=request.form["comment"])

    return redirect("/tag/" + request.form["tag"] + "#comment-" + str(comment.id))

  else:
    return render_template("comment.invalid-captcha.html")

@app.route("/recent-comments.xml")
@app.route("/recent-comments.rss")
def show_comments_feed():
  comments = []
  commentsout = []
  if Comment.table_exists():
    comments = Comment.select().where(Comment.active).order_by(Comment.id.desc()).paginate(1, 10)

  for comment in comments:
    comment.comment = sfm(comment.comment)
    commentsout.append(comment)

  return render_template("comments.xml", comments=commentsout)


@app.route("/recent-comments", defaults={"page": 1})
@app.route("/recent-comments/<int:page>")
def show_comments(page):
  PERPAGE = 20

  comments = []
  commentsout = []
  count = 0
  tags = 0
  if Comment.table_exists():
    comments = Comment.select().where(Comment.active).order_by(Comment.id.desc()).paginate(page, PERPAGE)
    count = Comment.select().where(Comment.active).count()
    tags = Comment.select(Comment.tag).where(Comment.active).distinct().count()

  for comment in comments:
    comment.comment = sfm(comment.comment)
    comment.breadcrumb = getBreadcrumb(Tag.get(Tag.tag == comment.tag))
    comment.tag = Tag.get(Tag.tag == comment.tag)

    commentsout.append(comment)

  return render_template(
      "comments.html",
      page=page,
      perpage=PERPAGE,
      comments=commentsout,
      count=count,
      tags=tags)
