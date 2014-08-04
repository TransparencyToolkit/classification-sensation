import classificate as C

for d in C.docs:
  try:
    d["doc_text"][0]
    pass
  except:
    print C.uniquify(d)
    pass
  pass
