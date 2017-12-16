from peewee import *
from playhouse.sqlite_ext import *

import gerby.config as config

db = SqliteExtDatabase(config.DATABASE)

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

class TagSearch(FTSModel):
  tag = SearchField(unindexed=True)
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

  def __gt__(self, other):
    return self.tag > other.tag

class Extra(BaseModel): # contains extra information such as slogans
  # TODO right now it doesn't say the *type* of extra information
  tag = ForeignKeyField(Tag)
  html = TextField(null=True)

class Footnote(BaseModel):
  label = CharField(unique=True, primary_key=True)
  html = TextField(null=True)

# TODO maybe just put this in Tag?
class LabelName(BaseModel):
  tag = ForeignKeyField(Tag)
  name = CharField()

class BibliographyEntry(BaseModel):
  key = CharField(unique=True, primary_key=True)
  entrytype = CharField()

  def __gt__(self, other):
    if hasattr(self, "author") and hasattr(other, "author"):
      return self.author.lower() > other.author.lower()
    else:
      return self.key.lower() > other.key.lower()

class Citation(BaseModel):
  tag = ForeignKeyField(Tag, unique=True)
  key = ForeignKeyField(BibliographyEntry)

class BibliographyField(BaseModel):
  key = ForeignKeyField(BibliographyEntry)
  field = CharField()
  value = CharField()
