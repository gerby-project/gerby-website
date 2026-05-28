from flask import render_template

from gerby.application import app
from gerby.database import *


def decorateEntries(entries):
  # Fetch every BibliographyField for the given entries in a single query
  # and attach the values both as attributes (used by the overview template
  # and by __gt__ for sorting) and via the entry.fields dict (used by the
  # entry detail template).
  entries = list(entries)
  if not entries:
    return entries

  by_key = {entry.key: entry for entry in entries}
  for entry in entries:
    entry.fields = {}

  for field in (BibliographyField
                .select()
                .where(BibliographyField.key << list(by_key))):
    entry = by_key.get(field.key_id)
    if entry is None:
      continue
    setattr(entry, field.field, field.value)
    entry.fields[field.field] = field.value

  return entries


@app.route("/bibliography")
def show_bibliography():
  entries = sorted(decorateEntries(BibliographyEntry.select()))

  return render_template("bibliography.overview.html", entries=entries)


@app.route("/bibliography/<string:key>")
def show_entry(key):
  # Decorating every entry in one bulk query is much cheaper than running a
  # per-entry query, even though we only need the neighbours; we also reuse
  # the resulting entry instance to avoid a separate fetch for its fields.
  entries = sorted(decorateEntries(BibliographyEntry.select()))

  index = -1
  for i, candidate in enumerate(entries):
    if candidate.key == key:
      index = i
      break

  if index == -1:
    return render_template("bibliography.notfound.html", key=key), 404

  entry = entries[index]

  neighbours = [None, None]
  if index > 0:
    neighbours[0] = entries[index - 1]
  if index < len(entries) - 1:
    neighbours[1] = entries[index + 1]

  # Join Tag so the template's citation.tag.* accesses (and the __gt__ used
  # when sorting) don't issue a separate Tag query per citation.
  citations = sorted(Citation
                     .select(Citation, Tag)
                     .join(Tag, on=Citation.tag)
                     .where(Citation.key == entry.key))

  return render_template("bibliography.entry.html",
                         entry=entry,
                         neighbours=neighbours,
                         citations=citations)
