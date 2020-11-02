import hashlib

from flask import render_template, send_from_directory, redirect
from datetime import datetime

from gerby.application import app
from gerby.database import *
from gerby.views.methods import *
import gerby.views.tag
from gerby.configuration import *

import json
import networkx as nx

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

  with app.open_resource("tex/documentation/support", mode="r") as f:
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

  with app.open_resource("tex/CONTRIBUTORS") as f:
    for line in f:
      line = line.decode("utf-8")
      if line.startswith("%") or line.isspace():
        continue
      contributors.append(line)

  return render_template("single/contributors.html", contributors=contributors)


@app.route("/api")
def show_api():
  return render_template("single/api.html")


@app.route("/data/tag/<string:tag>/structure")
def show_api_structure(tag):
  # little helper function to turn the output of gerby.views.tag.combine() into a dict (for JSON output)
  def jsonify(tag):
    output = dict()

    output["tag"] = tag.tag
    output["type"] = tag.type
    output["reference"] = tag.ref
    if tag.name:
      output["name"] = tag.name

    if hasattr(tag, "children"):
      output["children"] = [jsonify(child) for child in tag.children]

    return output


  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  # probably need nicer errors in the API: what would people find convenient?
  if tag.type not in gerby.views.tag.headings:
    return "This tag does not have a structure."
  # modified from show_tag for headings
  else:
    # if the tag is a part, we select all chapters, and then do the startswith for these
    if tag.type == "part":
      chapters = Part.select(Part.chapter).where(Part.part == tag.tag)
      chapters = Tag.select().where(Tag.tag << [chapter.chapter.tag for chapter in chapters])

      prefixes = tuple(chapter.ref + "." for chapter in chapters)
      # instead of sections we now select *all* tags, which can be slow'ish
      sections = Tag.select()
      sections = filter(lambda section: section.ref.startswith(prefixes), sections)

      tags = list(chapters) + list(sections)

    else:
      tags = Tag.select(Tag).where(Tag.ref.startswith(tag.ref + "."))

    tree = gerby.views.tag.combine(sorted(tags))

    tag.children = tree
    return json.dumps(jsonify(tag), indent=2)


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
    if gerby.views.tag.headings.index(tag.type) >= gerby.views.tag.headings.index(UNIT):
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
    if gerby.views.tag.headings.index(tag.type) >= gerby.views.tag.headings.index(UNIT):
      tags = Tag.select().where(Tag.ref.startswith(tag.ref + "."), Tag.type << gerby.views.tag.headings)
      html = html + "".join([item.html for item in sorted(tags)])

  # it's a tag (maybe with proofs)
  else:
    proofs = Proof.select().where(Proof.tag == tag.tag)
    html = tag.html + "".join([proof.html for proof in proofs])

  return html


structure = None
references = None

# preparing the data structure for the graphs
# need to collect all data in one go
# this is put into a separate function to avoid initalization problems
# TODO it would be better to do this differently, but this at least fixes the problems that people experience, for now
def initialize_dependencies():
  if structure != None and references != None:
    return

  tags = Tag.select().prefetch(Dependency)
  
  # dictionary of tags with keys the tags
  structure = dict()
  for tag in tags:
    structure[tag.tag] = tag
  
  # dictionary of tags with keys the references
  references = dict()
  for tag in tags:
    # ignore these
    if tag.type in ["item", "part"]:
      continue
  
    references[tag.ref] = tag


@app.route("/tag/<string:tag>/graph/topics")
def show_topics_graph(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  return render_template("stacks/graph.topics.html", tag=tag)


@app.route("/data/tag/<string:tag>/graph/topics")
def show_topics_data(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  # TODO avoid this
  initalize_dependencies()

  # these will contain the actual chapter and section numbers
  chapters = set()
  sections = set()

  # only visit tags once
  tags = set()

  # recursing through the tags
  def recurse(tag):
    tags.add(tag.tag)

    for child in structure[tag.tag].outgoing:
      if child.to.type == "item":
        continue

      chapter = child.to.ref.split(".")[0]
      section = ".".join(child.to.ref.split(".")[0:2])

      chapters.add(chapter)
      sections.add(section)

      if child.to.tag not in tags:
        recurse(child.to)

  # collect all used sections
  recurse(tag)

  # create the JSON dict for the output
  data = []

  # collect the actual tag information
  for chapter in chapters:
    chapter = references[chapter]

    output = {"tag": chapter.tag, "ref": chapter.ref, "name": chapter.name, "children": []}

    for section in [ref for ref in sections if ref.split(".")[0] == chapter.ref]:
      section = references[section]

      output["children"].append({"tag": section.tag, "ref": section.ref, "name": section.name})

    data.append(output)

  return json.dumps(data, indent=2)


@app.route("/tag/<string:tag>/graph/structure")
def show_structure_graph(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  return render_template("stacks/graph.structure.html", tag=tag)


@app.route("/data/tag/<string:tag>/graph/structure")
def show_graph_data(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  # TODO avoid this
  initalize_dependencies()

  data = dict()
  data["nodes"] = []
  data["links"] = []

  # only visit tags once
  tags = set()

  # recursing through the tags
  def recurse(tag):
    tags.add(tag.tag)

    data["nodes"].append({"tag": tag.tag, "ref": tag.ref})

    for child in structure[tag.tag].outgoing:
      data["links"].append({"source": tag.tag, "target": child.to.tag})

      if child.to.tag not in tags:
        recurse(child.to)

  # collect all used tags
  recurse(tag)

  # computing statistics
  G = nx.DiGraph()
  [G.add_node(node["tag"]) for node in data["nodes"]]
  [G.add_edge(link["source"], link["target"]) for link in data["links"]]
  # TODO fails for 0E9C
  #assert nx.is_directed_acyclic_graph(G)

  depths = dict(nx.single_source_shortest_path_length(G, tag.tag))
  sizes = {node["tag"]: len(nx.descendants(G, node["tag"])) for node in data["nodes"]}

  # assigning statistics
  for node in data["nodes"]:
    node["depth"] = depths[node["tag"]]
    node["size"] = sizes[node["tag"]]


  # dictionary from tags to positions (because D3 works like that)
  positions = {node["tag"]: position for (position, node) in enumerate(data["nodes"])}

  # replace tags with positions
  data["links"] = [{"source": positions[link["source"]], "target": positions[link["target"]]} for link in data["links"]]

  return json.dumps(data, indent=2)


@app.route("/tag/<string:tag>/graph/tree")
def show_tree_graph(tag):
  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  return render_template("stacks/graph.dendrogram.html", tag=tag)


TREE_LEVEL = 4
@app.route("/data/tag/<string:tag>/graph/tree")
def show_tree_data(tag):
  # TODO avoid this
  initalize_dependencies()

  # recursive method to populate the tree
  def populate_tree(tag, level=0):
    data = dict()

    # the information that we display
    data["tag"] = tag.tag
    data["ref"] = tag.ref
    data["type"] = tag.type
    if tag.name:
      data["name"] = tag.name

    if level < TREE_LEVEL:
      children = structure[tag.tag].outgoing

      if len(children) > 0:
        data["children"] = [populate_tree(child.to, level + 1) for child in children]

    return data

  if not gerby.views.tag.isTag(tag):
    return "This is not a valid tag."

  try:
    tag = Tag.get(Tag.tag == tag)
  except Tag.DoesNotExist:
    return "This tag does not exist."

  data = populate_tree(tag)
  return json.dumps(data, indent=2)


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

  if Change.table_exists():
    changes = Change.select().join(Commit).where(Change.tag == tag).order_by(Commit.time.desc())
    for change in changes:
      change.commit.time = change.commit.time.decode("utf-8").split(" ")[0] # why in heaven's name is this returning bytes?!

    if len(changes) > 0:
      return render_template("tag.history.html",
                             tag=tag,
                             changes=changes,
                             filename=tag.label.split("-" + tag.type)[0],
                             breadcrumb=breadcrumb,
                             neighbours=neighbours)

  # this means something went wrong
  return render_template("tag.history.empty.html", tag=tag, breadcrumb=breadcrumb)


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

