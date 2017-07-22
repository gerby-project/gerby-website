from peewee import *

import re
import os
import os.path
import logging, sys

logging.basicConfig(stream=sys.stdout)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


PATH = "book"
db = SqliteDatabase("stacks.sqlite")

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

class Proof(BaseModel):
  tag = ForeignKeyField(Tag, related_name = "proofs")
  html = TextField(null=True)
  number = IntegerField() # TODO (tag,number) is unique

class Dependency(BaseModel):
  tag = ForeignKeyField(Tag, related_name="from")
  to = ForeignKeyField(Tag, related_name="to")


# create database if it doesn't exist already
if not os.path.isfile("stacks.sqlite"):
  db.create_tables([Tag, Proof, Dependency])
  log.info("Created database")


# the information on disk
files = [f for f in os.listdir(PATH) if os.path.isfile(os.path.join(PATH, f)) and f != "index"] # index is always created
tagFiles = [filename for filename in files if filename.endswith(".tag")]
proofFiles = [filename for filename in files if filename.endswith(".proof")]

# import tags
log.info("Importing tags")
for filename in tagFiles:
  with open(os.path.join(PATH, filename)) as f:
    value = f.read()

  filename = filename[:-4]
  pieces = filename.split("-")

  tag, created = Tag.get_or_create(tag=pieces[2])

  if created:
    log.info("Created tag %s", pieces[2])
  else:
    if tag.label != "-".join(pieces[3:]):
      log.info("Tag %s: label has changed", tag.tag)
    if tag.html != value:
      log.info("Tag %s: content has changed", tag.tag)
    if tag.type != pieces[0]:
      log.info("Tag %s: type has changed", tag.tag)

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
    log.info("Tag %s: created proof #%s", proof.tag.tag, proof.number)
  else:
    if proof.html != value:
      log.info("Tag %s: proof #%s has changed", proof.tag.tag, pieces[1])

  proof.html = value
  proof.save()


# check (in)activity of tags
log.info("Checking inactivity")
with open("tags") as f:
  tags = f.readlines()
  tags = [line.strip() for line in tags if not line.startswith("#")]
  tags = dict([line.split(",") for line in tags if "," in line])

  for tag in Tag.select():
    if tag.tag not in tags:
      Tag.update(active=False).where(Tag.tag == tag.tag)
      log.info("Tag %s became inactive", tag.tag)
    else:
      if tag.label != tags[tag.tag]:
        log.error("Labels for tag %s differ from tags file to database:\n  %s\n  %s", tag.tag, tags[tag.tag], tag.label)


# create dependency data
log.info("Creating dependency data")
Dependency.drop_table()
db.create_table(Dependency)

for proof in Proof.select():
  regex = re.compile(r'<a href=\"/tag/([0-9A-Z]{4})\">')
  with db.atomic():
    dependencies = regex.findall(proof.html)

    if len(dependencies) > 0:
      Dependency.insert_many([{"tag": proof.tag.tag, "to": to} for to in dependencies]).execute()
