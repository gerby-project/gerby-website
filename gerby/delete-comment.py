from gerby.database import *
import gerby.configuration

import sys

# we put this file in this directory, otherwise the path to the database isn't correct

for id in sys.argv[1:]:
  id = int(id)
  try:
    comment = Comment.get(Comment.id == id)
    comment.active = not comment.active

    if comment.active: print("Made comment %d active" % id)
    else: print("Made comment %d inactive" % id)

    comment.save()
  except Comment.DoesNotExist:
    print("ERROR: Comment %d does not exist" % id)
    pass

