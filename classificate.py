import json
import re
import sys
import time

# I'm not going to check for failure here.  You figure it out.
with open("docs2.json", 'r') as f: docs = json.load(f)
with open("isocodes.json", 'r') as f: codes = json.load(f)
two_codes = dict([(
  codes[i]["two_letter_iso"], codes[i]["full_name"])
                    for i in codes.keys()])
three_codes = dict([(
  codes[i]["three_letter_iso"], codes[i]["full_name"])
                    for i in codes.keys()])

def clean(s): return \
  filter(lambda c: 0x20 <= ord(c) <= 0x7E or c in "\n\r\t", s).lower().strip()

def get_time(doc, field):
  if doc[field] is None or doc[field].startswith("0000-00-00"):
    return "nodate"

  for f in ["%Y%m%d", "%Y-%m-%d", "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
    try: return time.strftime("%Y%m%d", time.strptime(doc[field], f))
    except: pass
    pass

  raise ValueError("No good times found in %s" % doc[field])

def date(doc):
  date = get_time(doc, "released_date")
  doc["released_date"] = date

def identify(doc):
  date = doc["released_date"]
  title = doc["title"]

  fields = [date, title]
  doc["id"] = clean('|'.join(fields).replace(" ", "").replace("/", ""))

def dock(cs):
  for c in ["ts", "s", "c", "pt", "cui", "u"]:
    if reduce(lambda acc, x: acc or x.startswith(c), cs, False):
      return c.upper()
    pass
  return None

def getclassification(p):
  res = dock(re.findall("(?<=\()" + ".*?" + "(?=/+.*\))", p))
  if res: return res

  res = dock(re.findall("(?<=\()" + "[a-z]*?" + "(?=\))", p))
  if res: return res

  if "topsecret" in p: return "TS"
  elif "secret" in p: return "S"
  elif "confidential" in p: return "C"
  elif "publictrust" in p: return "PT"
  elif "controlledunclassifiedinformation" in p: return "CUI"
  elif "unclassified" in p: return "U"

  return None

def getrelto(p):
  raw = clean(''.join(re.findall("(?<=relto)" + "[^\\n\)]*", p)))
  raw = filter(lambda c: 'a' < c < 'z', raw).upper()

  shared = []
  if "FVEY" in raw:
    shared += ["Australia", "Canada", "New Zealand", "United States", "Great Britain"]
    raw = raw.replace("FVEY", " ")
    pass
  for code in three_codes.keys():
    if three_codes[code] in raw:
      shared.append(three_codes[code])
      raw = raw.replace(code, " ")
      pass
    pass
  for code in two_codes.keys():
    if code in raw:
      shared.append(two_codes[code])
      raw = raw.replace(code, " ")
      pass
    pass

  return list(set(shared))

def getcaveats(p):
  # This is simple, but in practice will generate a lot of both false
  # positives and false negatives.
  #
  # The false positives occur because we are overgenerous on our matching of
  # paren-bounded slash-delimited terms.
  #
  # The false negatives occur because it is infeasible to run over the raw
  # document ignoring the parens because what the classification levels are
  # named is itself classified.

  raw = re.findall("(?<=\()" + "[a-z/]*?/[a-z/]*?" + "(?=\))", p)
  raw = map(lambda e: e.split("/")[1:], raw)
  raw = reduce(lambda acc, x: acc + x, raw, [])
  raw = filter(lambda e: not (e == "" or e == None), raw)
  raw = list(set(raw))
  return raw

def paragraphs(doc):
  ps = map(lambda p: clean(p), doc["doc_text"].splitlines())
  i = 0
  psaux = []
  while True:
    if i >= len(ps):
      break
    t = ps[i].replace(" ", "")
    if t in [None, ""]:
      del(ps[i])
      continue

    d = {}
    d["paragraph_text"] = ps[i] + " "
    d["paragraph_classification"] = getclassification(t)
    d["paragraph_relto"] = getrelto(t)
    d["paragraph_handling_caveats"] = getcaveats(t)
    psaux.append(d)

    i += 1
    pass
  del(i)
  doc["sub_paragraphs_classifications"] = psaux

  return

def overall(doc):
  # Hopefully, the article classification is the first one.
  psaux = doc["sub_paragraphs_classifications"]

  try: doc["overall_classification"] = psaux[0]["paragraph_classification"]
  except: doc["overall_classification"] = None

  try: doc["overall_relto"] = psaux[0]["paragraph_relto"]
  except: doc["overall_relto"] = []

  try: doc["overall_handling_caveats"] = \
     psaux[0]["paragraph_overall_handling_caveats"]
  except: doc["overall_handling_caveats"] = []

  return

i = 0
while True:
  if i >= len(docs):
    break

  try:
    docs[i]["doc_text"][0]
  except:
    del(docs[i])
    continue
    pass

  i += 1
  pass
del(i)

for d in docs:
  date(d)
  identify(d)
  paragraphs(d)
  overall(d)

  i = 0
  while True:
    if i >= len(d["sub_paragraphs_classifications"]):
      break
    elif d["sub_paragraphs_classifications"][i]["paragraph_classification"] \
         is None and i > 0:
      for f in d["sub_paragraphs_classifications"][i].keys():
        if d["sub_paragraphs_classifications"][i][f] is not None:
          d["sub_paragraphs_classifications"][i-1][f] \
            += d["sub_paragraphs_classifications"][i][f]
          pass
        pass
      del(d["sub_paragraphs_classifications"][i])
      continue
    i += 1
    pass
  del(i)
  pass
pass

print json.dumps(docs, check_circular=False, indent=2, encoding="ascii") # enjoy
