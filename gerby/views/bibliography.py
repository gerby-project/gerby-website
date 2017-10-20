from flask import render_template

from gerby.gerby import app
from gerby.database import *

@app.route("/bibliography")
def show_bibliography():
  entries = BibliographyEntry.select()

  for entry in entries:
    fields = BibliographyField.select().where(BibliographyField.key == entry.key)
    for field in fields:
      setattr(entry, field.field, field.value)

  entries = sorted(entries)

  return render_template("show_bibliography.html", entries=entries)

@app.route("/bibliography/<string:key>")
def show_entry(key):
  entry = BibliographyEntry.get(BibliographyEntry.key == key)

  fields = BibliographyField.select().where(BibliographyField.key == entry.key)
  entry.fields = dict()
  for field in fields:
    entry.fields[field.field] = field.value

  return render_template("show_entry.html", entry=entry)
