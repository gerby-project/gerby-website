from peewee import *
from playhouse.sqlite_ext import *

import re
import os
import os.path
import logging, sys
import pickle

logging.basicConfig(stream=sys.stdout)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


PATH = "htt"
FILENAME = "htt.sqlite"
PAUX = "htt.paux"
TAGS = "tags.htt"

db = SqliteExtDatabase(FILENAME)

class BaseModel(Model):
  class Meta:
    database = db

class Tag(BaseModel):
  tag = CharField(unique=True, primary_key=True)
  label = CharField(unique=True, null=True)
  active = BooleanField(null=True)
  ref = CharField(null=True) # TODO unique=True?
  type = CharField(null=True)
  html = TextField(null=True)

class TagSearch(FTSModel):
  tag = SearchField()
  html = SearchField() # HTML of the statement or (sub)section
  full = SearchField() # HTML of the statement including the proof (if relevant)

  class Meta:
    database = db

class Proof(BaseModel):
  tag = ForeignKeyField(Tag, related_name = "proofs")
  html = TextField(null=True)
  number = IntegerField() # TODO (tag,number) is unique

class Dependency(BaseModel):
  tag = ForeignKeyField(Tag, related_name="from")
  to = ForeignKeyField(Tag, related_name="to")

class Extra(BaseModel):
  tag = ForeignKeyField(Tag)
  html = TextField(null=True)

# TODO maybe just put this in Tag?
class LabelName(BaseModel):
  tag = ForeignKeyField(Tag)
  name = CharField()


# create database if it doesn't exist already
if not os.path.isfile(FILENAME):
  db.create_tables([Tag, Proof, Extra])
  log.info("Created database")


# the information on disk
files = [f for f in os.listdir(PATH) if os.path.isfile(os.path.join(PATH, f)) and f != "index"] # index is always created
tagFiles = [filename for filename in files if filename.endswith(".tag")]
proofFiles = [filename for filename in files if filename.endswith(".proof")]

extras = ("slogan", "history")
extraFiles = [filename for filename in files if filename.endswith(extras)]

context = pickle.load(open(os.path.join(PAUX), "rb"))

with open(TAGS) as f:
  tags = f.readlines()
  tags = [line.strip() for line in tags if not line.startswith("#")]
  tags = dict([line.split(",") for line in tags if "," in line])
  labels = {item: key for key, item in tags.items()}

# import tags
log.info("Importing tags")
for filename in tagFiles:
  with open(os.path.join(PATH, filename)) as f:
    value = f.read()

  filename = filename[:-4]
  pieces = filename.split("-")

  tag, created = Tag.get_or_create(tag=pieces[2])

  if created:
    log.info("  Created tag %s", pieces[2])
  else:
    if tag.label != "-".join(pieces[3:]):
      log.info("  Tag %s: label has changed", tag.tag)
    if tag.html != value:
      log.info("  Tag %s: content has changed", tag.tag)
    if tag.type != pieces[0]:
      log.info("  Tag %s: type has changed", tag.tag)

  tag.label = "-".join(pieces[3:])
  tag.ref = pieces[1]
  tag.type = pieces[0]
  tag.html = value

  tag.save()


# import proofs
log.info("Importing proofs")
for filename in proofFiles:
  with open(os.path.join(PATH, filename)) as f:
    value = f.read()

  filename = filename[:-6]
  pieces = filename.split("-")

  proof, created = Proof.get_or_create(tag=pieces[0], number=int(pieces[1]))

  if created:
    log.info("  Tag %s: created proof #%s", proof.tag.tag, proof.number)
  else:
    if proof.html != value:
      log.info("Tag %s: proof #%s has changed", proof.tag.tag, pieces[1])

  proof.html = value
  proof.save()


# create search table
log.info("Populating the search table")
if TagSearch.table_exists():
  TagSearch.drop_table()
db.create_table(TagSearch)

for tag in Tag.select():
  proof = Proof.select().where(Proof.tag == tag.tag).order_by(Proof.number)

  TagSearch.insert({
    TagSearch.tag: tag.tag,
    TagSearch.html: tag.html,
    TagSearch.full: tag.html, # TODO collate with proofs
    }).execute()



# check (in)activity of tags
log.info("Checking inactivity")
for tag in Tag.select():
  if tag.tag not in tags:
    log.info("  Tag %s became inactive", tag.tag)
    tag.active = False
  else:
    if tag.label != tags[tag.tag]:
      log.error("  Labels for tag %s differ from tags file to database:\n  - %s\n  - %s", tag.tag, tags[tag.tag], tag.label)
    else:
      tag.active = True

  tag.save()


# create dependency data
log.info("Creating dependency data")
if Dependency.table_exists():
  Dependency.drop_table()
db.create_table(Dependency)

for proof in Proof.select():
  regex = re.compile(r'<a href=\"/tag/([0-9A-Z]{4})\">')
  with db.atomic():
    dependencies = regex.findall(proof.html)

    if len(dependencies) > 0:
      Dependency.insert_many([{"tag": proof.tag.tag, "to": to} for to in dependencies]).execute()


# import history, slogans, etc
log.info("Importing history, slogans, etc.")
for filename in extraFiles:
  with open(os.path.join(PATH, filename)) as f:
    value = f.read()

  pieces = filename.split(".")

  extra, created = Extra.get_or_create(tag=pieces[0])

  if created:
    log.info("  Tag %s: added a %s", extra.tag.tag, pieces[1])
  else:
    if extra.html != value:
      log.info("  Tag %s: %s has changed", extra.tag.tag, pieces[1])

  extra.html = value
  extra.save()


# import names of labels
log.info("Importing names of tags")
if LabelName.table_exists():
  LabelName.drop_table()
db.create_table(LabelName)

names = list()

for key, item in context["Gerby"].items():
  if "title" in item and key in labels:
    # TODO pickle does not reconstruct plasTeX.TeXFragment, which is used for some labels with accents...
    if "TeX" in item["title"]:
      print(item)

    names.append({"tag" : labels[key], "name" : item["title"]})

with db.atomic():
  chunk = 100 # despite its name, Model.insert_many cannot insert too many at the same time
  for i in range(0, len(names), chunk):
    LabelName.insert_many(names[i:i+chunk]).execute()
