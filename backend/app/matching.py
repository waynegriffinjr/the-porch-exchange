"""Concept-based matching between needs and the skills neighbors offer.

Words are reduced to a stem and mapped to a concept (e.g. "ride" and "driving" are both `drive`).
Generic words such as "repair" or "help" never count on their own. A skill matches a need when
most of the skill *name's* concepts appear in the need, or, failing that, when at least two
concepts from the skill's details do. A single stray word in the details never creates a match.
"""

import re

# Each group is a list of interchangeable words; the first word names the concept.
SYNONYM_GROUPS = [
    ["drive", "driving", "driver", "ride", "rides", "transport", "transportation", "carpool", "lift"],
    ["move", "moving", "mover", "movers", "relocate", "relocation"],
    ["haul", "hauling", "dump", "junk", "trailer", "debris"],
    ["lawn", "mow", "mowing", "mower", "grass", "yard", "leaf", "leaves"],
    ["landscape", "landscaping", "hedge", "hedges", "shrub", "mulch", "tree", "trees"],
    ["garden", "gardening", "weed", "weeding", "vegetable", "vegetables", "flower", "flowers", "planting"],
    ["snow", "shovel", "shoveling", "plow", "plowing", "driveway"],
    ["cook", "cooking", "meal", "meals", "dinner", "dinners", "lunch", "food", "homemade", "recipe"],
    ["bake", "baking", "bread", "pie", "pies", "cake", "cakes", "cupcake", "cupcakes", "cookie", "cookies", "pastry"],
    ["can", "canning", "preserve", "preserves", "jam", "pickle", "pickles"],
    ["tax", "taxes", "irs"],
    ["bookkeep", "bookkeeping", "budget", "receipts", "accounting", "accountant", "spreadsheet", "spreadsheets"],
    ["paperwork", "legal", "will", "wills", "forms", "notice", "notices"],
    ["notary", "notarize", "notarizing"],
    [
        "computer",
        "laptop",
        "pc",
        "tech",
        "technology",
        "smartphone",
        "phone",
        "wifi",
        "wi-fi",
        "printer",
        "internet",
        "software",
        "virus",
        "email",
    ],
    ["tutor", "tutoring", "homework", "teach", "teaching", "lesson", "lessons"],
    ["child", "children", "childcare", "babysit", "babysitting", "babysitter", "nanny"],
    ["pet", "pets", "dog", "dogs", "cat", "cats", "puppy", "animal", "animals"],
    ["companion", "companionship"],
    ["resume", "cv", "interview", "job"],
    ["sew", "sewing", "hem", "hemming", "alteration", "alterations", "clothing", "tailor", "mend", "mending"],
    ["quilt", "quilting", "quilts"],
    ["knit", "knitting", "crochet"],
    ["paint", "painting", "painter"],
    ["plumb", "plumbing", "plumber", "faucet", "drain", "leak", "leaky", "leaking", "sink", "toilet", "pipe"],
    ["electric", "electrical", "electrician", "outlet", "outlets", "wiring", "switch", "fixture"],
    ["auto", "car", "vehicle", "brake", "brakes", "battery", "oil"],
    ["engine", "chainsaw", "trimmer"],
    ["bicycle", "bike", "bikes", "bicycles"],
    ["firewood", "wood", "log", "logs", "split", "splitting"],
    ["hair", "haircut", "haircuts", "barber"],
    ["photo", "photos", "photography", "photograph", "portrait", "portraits", "picture", "pictures"],
    ["translate", "translation", "translator", "interpreter"],
    ["carpentry", "carpenter", "fence", "shelf", "shelves", "deck"],
    ["concrete", "cement", "patio", "walkway", "walkways", "sidewalk"],
    ["weld", "welding", "welder"],
    ["nurse", "nursing", "medication", "medications", "blood"],
    ["yoga", "stretching"],
    ["grocery", "groceries", "pharmacy", "errand", "errands"],
]

# Words too broad to indicate a specific skill on their own.
GENERIC_WORDS = frozenset(
    "repair repairs fix fixing help helper helping care service services work home house support setup set "
    "up sit sitting removal delivery deliver general basic assistance family families neighbor neighbors "
    "week month year summer winter morning evening weekend sunday monday tuesday wednesday thursday friday "
    "saturday new old small big elder elderly senior seniors kid kids cut cutting".split()
)

STOPWORDS = frozenset(
    "a an and are as at be been but by can could do for from get got has have i in is it its me my need needs "
    "needed of on or our so some that the their them this to us we with would you your want wants looking "
    "someone anyone able also each any all not no than then too very will may might must".split()
)


def stem(word: str) -> str:
    """Very light stemmer so 'mowing', 'mows' and 'mow' compare equal."""
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "ie"
    elif word.endswith("ing") and len(word) > 5:
        word = word[:-3]
        if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":
            word = word[:-1]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        word = word[:-1]
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


CONCEPTS: dict[str, str] = {}
for _group in SYNONYM_GROUPS:
    for _word in _group:
        CONCEPTS.setdefault(stem(_word), stem(_group[0]))
GENERIC_STEMS = frozenset(stem(w) for w in GENERIC_WORDS)


def specific_stems(text: str | None) -> set[str]:
    """Stems of the meaningful (non-stopword, non-generic) words in the text."""
    stems = set()
    for raw in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower()):
        if raw not in STOPWORDS and len(raw) >= 3 and stem(raw) not in GENERIC_STEMS:
            stems.add(stem(raw))
    return stems


def concepts(text: str | None) -> set[str]:
    """Concepts (synonym groups collapsed) for the meaningful words in the text."""
    return {CONCEPTS.get(s, s) for s in specific_stems(text)}


def score_match(need_title: str, need_description: str | None, skill_name: str, skill_description: str | None) -> int:
    """Score how well a skill fits a need; 0 means no match.

    - Name match: more than half of the skill name's concepts appear in the need (4 points each).
    - Detail match: otherwise, at least two concepts or words from the skill's details appear (1 point each).
    Concepts in the need's title and description both count.
    """
    need_text = f"{need_title} {need_description or ''}"
    need_concepts = concepts(need_text)
    name_concepts = concepts(skill_name)
    name_hits = need_concepts & name_concepts
    if name_concepts and len(name_hits) / len(name_concepts) > 0.5:
        detail_hits = (need_concepts & concepts(skill_description)) - name_hits
        return 4 * len(name_hits) + min(len(detail_hits), 2)

    # Count shared concepts or shared exact words, whichever is larger.
    detail_hits = max(
        len(need_concepts & concepts(skill_description)),
        len(specific_stems(need_text) & specific_stems(skill_description)),
    )
    return detail_hits if detail_hits >= 2 else 0
