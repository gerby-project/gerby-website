import markdown
from mdx_bleach.extension import BleachExtension
from mdx_bleach.whitelist import ALLOWED_TAGS
from mdx_bleach.whitelist import ALLOWED_ATTRIBUTES
from mdx_math import MathExtension

from gerby.database import *

# TODO organise this a bit more efficiently?

def is_math(tag, name, value):
  return name == "type" and value in ["math/tex", "math/tex; mode=display"]


# Stacks flavored Markdown parser
def sfm(comment):
  attributes = ALLOWED_ATTRIBUTES
  attributes["span"] = ["class"]
  attributes["script"] = is_math

  tags = ALLOWED_TAGS + ["span", "script"]

  bleach = BleachExtension(tags=tags, attributes=attributes)
  math = MathExtension(enable_dollar_delimiter=True)
  md = markdown.Markdown(extensions=[math, bleach])

  # Stacks flavored Markdown: only \ref{tag}, no longer \ref{label}
  references = re.compile(r"\\ref\{([0-9A-Z]{4})\}").findall(comment)
  for reference in references:
    comment = comment.replace("\\ref{" + reference + "}", "[<span class=\"tag\">" + reference + "</a>](/tag/" + reference + ")")
    # TODO use <span class="tag"> here (allow it in Bleach, etc.)

  comment = md.convert(comment)

  return comment


def getBreadcrumb(tag):
  if tag.type == "part":
    return [tag]

  pieces = tag.ref.split(".")
  refs = [".".join(pieces[0:i]) for i in range(len(pieces) + 1)]

  tags = Tag.select().where(Tag.ref << refs, ~(Tag.type << ["item", "part"]))
  tags = sorted(tags)

  # if there are parts, we look up the corresponding part and add it
  if Tag.select().where(Tag.type == "part").exists():
    chapter = tags[0]
    part = Part.get(Part.chapter == chapter.tag).part
    tags.insert(0, part)

  return tags


