from flask import redirect, render_template, request

from gerby.gerby import app
from gerby.database import *

import validators

@app.route("/post-comment", methods=["POST"])
def post_comment():
  if not validators.email(request.form["mail"]):
    print("Invalid email address")

  site = request.form["site"]
  # if site is not a valid url just leave empty
  if not validators.url(request.form["site"]):
    site = ""

  if request.form["tag"] != request.form["check"]:
    print("Invalid captcha")


  # TODO what is the best way of knowing which tag page it was sent from?
  comment = Comment.create(
      tag=request.form["tag"],
      author=request.form["name"],
      site=site,
      email=request.form["mail"],
      comment=request.form["name"])

  return ""
