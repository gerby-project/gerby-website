from gerby.configuration import *
import datetime
from peewee import *
from playhouse.sqlite_ext import *

db = SqliteExtDatabase(None)
comments = SqliteDatabase(COMMENTS);

class BaseModel(Model):
  class Meta:
    database = db

class CommentBaseModel(Model):
  class Meta:
    database = comments


# basic tag data
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


class Proof(BaseModel):
  tag = ForeignKeyField(Tag, backref="proofs")
  html = TextField(null=True)
  number = IntegerField()


class Part(BaseModel):
  part = ForeignKeyField(Tag)
  chapter = ForeignKeyField(Tag)


class Dependency(BaseModel):
  tag = ForeignKeyField(Tag, backref="outgoing")
  to = ForeignKeyField(Tag, backref="incoming")

  def __gt__(self, other):
    return self.tag > other.tag


class Footnote(BaseModel):
  label = CharField(unique=True, primary_key=True)
  html = TextField(null=True)


# search tables
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


# extras (make sure backref doesn't coincide with JOIN alias)
class Slogan(BaseModel):
  tag = ForeignKeyField(Tag, backref="slogans")
  html = TextField(null=True)


class Reference(BaseModel):
  tag = ForeignKeyField(Tag, backref="references")
  html = TextField(null=True)


class History(BaseModel):
  tag = ForeignKeyField(Tag, backref="histories")
  html = TextField(null=True)


# bibliography data
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


class BibliographyField(BaseModel):
  key = ForeignKeyField(BibliographyEntry, backref="fields")
  field = CharField()
  value = CharField()


class Citation(BaseModel):
  tag = ForeignKeyField(Tag, backref="citations")
  key = ForeignKeyField(BibliographyEntry)
  note = TextField(null=True)

  class Meta:
    primary_key = CompositeKey("tag", "key")

  def __gt__(self, other):
    return self.tag > other.tag


# history functionality
class Commit(BaseModel):
  hash = FixedCharField(max_length=40, unique=True, primary_key=True)
  author = TextField(null=True)
  log = TextField(null=True)
  time = DateTimeField(null=True)


class Change(BaseModel):
  tag = ForeignKeyField(Tag, backref="changes")
  commit = ForeignKeyField(Commit)
  action = TextField()
  filename = TextField()
  label = TextField()
  begin = IntegerField()
  end = IntegerField()


# statistics
class TagStatistic(BaseModel):
  tag = ForeignKeyField(Tag, backref="statistics")
  statistic = TextField()
  value = IntegerField()

class BookStatistic(BaseModel):
  statistic = TextField()
  value = IntegerField()


# comments
class Comment(CommentBaseModel):
  id = PrimaryKeyField()
  tag = TextField(Tag)
  author = TextField()
  site = TextField(null=True)
  email = TextField(null=True)
  date = DateTimeField(default=datetime.datetime.now)
  comment = TextField(null=True)
  active = BooleanField(default=True)
