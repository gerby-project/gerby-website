import datetime
from peewee import *
from playhouse.sqlite_ext import *

import gerby.config as config

db = SqliteExtDatabase(None)
comments = SqliteDatabase("comments.sqlite");

class BaseModel(Model):
  class Meta:
    database = db

class CommentBaseModel(Model):
  class Meta:
    database = comments

class Tag(BaseModel):
  tag = CharField(unique=True, primary_key=True)
  label = CharField(unique=True, null=True)
  active = BooleanField(null=True)
  ref = CharField(null=True)
  type = CharField(null=True)
  html = TextField(null=True)
  name = TextField(null=True)

  # allows us to sort tags according to their reference
  def __gt__(self, other):
    try:
      for (i, j) in zip(self.ref.split("."), other.ref.split(".")):
        if i.isdigit() and j.isdigit():
          if int(i) != int(j):
            return int(i) > int(j)
        elif i.isdigit() and not j.isdigit():
          return False
        elif not i.isdigit() and j.isdigit():
          return True
        else:
          if i != j:
            return i > j

      # if we got this far it should mean one is a substring of the other?
      return len(self.ref) > len(other.ref)

    except ValueError:
      return 0 # just do something, will need to implement a better version

class SearchTag(FTSModel):
  tag = SearchField(unindexed=True)
  html = SearchField()

  class Meta:
    database = db

class SearchStatement(FTSModel):
  tag = SearchField(unindexed=True)
  html = SearchField()

  class Meta:
    database = db

class Proof(BaseModel):
  tag = ForeignKeyField(Tag, related_name = "proofs")
  html = TextField(null=True)
  number = IntegerField()

class Part(BaseModel):
  part = ForeignKeyField(Tag, related_name = "part")
  chapter = ForeignKeyField(Tag, related_name = "chapter")


class Dependency(BaseModel):
  tag = ForeignKeyField(Tag, related_name="from")
  to = ForeignKeyField(Tag, related_name="to")

  def __gt__(self, other):
    return self.tag > other.tag

class Slogan(BaseModel):
  tag = ForeignKeyField(Tag)
  slogan = TextField(null=True)


class Reference(BaseModel):
  tag = ForeignKeyField(Tag)
  reference = TextField(null=True)


class History(BaseModel):
  tag = ForeignKeyField(Tag)
  history = TextField(null=True)


class Footnote(BaseModel):
  label = CharField(unique=True, primary_key=True)
  html = TextField(null=True)

class BibliographyEntry(BaseModel):
  key = CharField(unique=True, primary_key=True)
  entrytype = CharField()
  code = CharField()

  def __gt__(self, other):
    if hasattr(self, "author") and hasattr(other, "author"):
      if self.author.lower() == other.author.lower() and hasattr(self, "title") and hasattr(other, "title"):
        return self.title.lower() > other.title.lower()
      return self.author.lower() > other.author.lower()
    else:
      return self.key.lower() > other.key.lower()

class Citation(BaseModel):
  tag = ForeignKeyField(Tag)
  key = ForeignKeyField(BibliographyEntry)

class BibliographyField(BaseModel):
  key = ForeignKeyField(BibliographyEntry)
  field = CharField()
  value = CharField()

class Comment(CommentBaseModel):
  id = PrimaryKeyField()
  tag = TextField(Tag)
  author = TextField()
  site = TextField(null=True)
  email = TextField(null=True)
  date = DateTimeField(default=datetime.datetime.now)
  comment = TextField(null=True)

class Commit(BaseModel):
  hash = FixedCharField(max_length=40, unique=True, primary_key=True)
  author = TextField(null=True)
  log = TextField(null=True)
  time = DateTimeField(null=True)

class Change(BaseModel):
  tag = ForeignKeyField(Tag)
  commit = ForeignKeyField(Commit)
  action = TextField()
  filename = TextField()
  label = TextField()
  begin = IntegerField()
  end = IntegerField()
