"""Spot "fixes" that make a test pass by hiding the problem.

A memory that records "added a 5 second sleep" as the fix teaches everyone the
same bad habit. Those lines are stored as `avoid`: shown as warnings, never
offered as guidance. Mentions that reject the shortcut ("not a fixed
timeout", "replaced the sleep with a response wait") are not flagged.
"""
import re

SHORTCUTS = [
    ("hard wait", r"waitForTimeout|\bThread\.sleep|\btime\.sleep|\bsleep\s*\(|\bcy\.wait\(\s*\d|\bhard[- ]?wait|"
                  r"fixed (?:wait|delay|timeout|pause)|\bsleep(?:s|ing)?\b|\bdelay of \d|\bwait(?:ed|ing)? \d+\s*(?:s|sec|seconds|ms)\b"),
    ("forced action", r"force\s*:\s*true|\{\s*force\b|\bforce[- ]?click|\bforced? the click"),
    ("raised timeout", r"(?:increas|rais|bump|extend|doubl)(?:e|ed|ing)? (?:the )?(?:global |default |test |action )?timeouts?|"
                       r"timeout\s*[:=]\s*\d{5,}|setTimeout\(\s*\d{5,}|\btest\.setTimeout\("),
    ("more retries", r"(?:increas|rais|add|bump)(?:e|ed|ing)? (?:the )?retr(?:y|ies)|\bretries\s*[:=]\s*[3-9]"),
    ("weakened assertion", r"(?:remov|delet|comment(?:ed)? out|drop|disabl|loosen|weaken)(?:e|ed|ing)? (?:the |an |that )?"
                           r"(?:assert(?:ion)?s?|expect(?:ation)?s?|checks?|verifications?)|toBeTruthy\(\)\s*instead|"
                           r"(?:changed|switched) (?:to )?toBeTruthy"),
    ("networkidle", r"networkidle"),
    ("swallowed error", r"catch\s*\(\s*\w*\s*\)\s*\{\s*\}|\.catch\(\s*\(\s*\)\s*=>\s*(?:\{\s*\}|null|undefined)\s*\)|"
                        r"ignore(?:d|s)? (?:the )?(?:error|exception)s?|swallow(?:ed|s)? (?:the )?(?:error|exception)"),
    ("absolute XPath", r"/html/body|xpath\s*=\s*/html"),
]
SHORTCUT_RE = [(label, re.compile(rx, re.I)) for label, rx in SHORTCUTS]
NEGATION = re.compile(r"\b(?:never|no|not|don't|dont|do not|avoid(?:ed|ing)?|instead of|rather than|without|"
                      r"replac(?:e|ed|ing)|remov(?:e|ed|ing)|got rid of|drop(?:ped)?|stop(?:ped)? using|"
                      r"swap(?:ped)?|instead)\b", re.I)


def find(text):
    """Shortcut labels the text recommends (mentions that reject the shortcut are ignored)."""
    if not text:
        return []
    # judge the fix, not the description of the problem
    fix = re.search(r"\b(?:fix(?:ed)?(?: by)?|solution|resolution|workaround|resolved by)\s*[:\-]", text, re.I)
    if fix:
        text = text[fix.end():]
    text = re.sub(r"\b(?:cause|root cause|symptom|problem)\s*:[^.;]*[.;]?", " ", text, flags=re.I)
    found = []
    for label, rx in SHORTCUT_RE:
        for m in rx.finditer(text):
            before = re.sub(r"\[[^\]]*\]", " ", text[max(0, m.start() - 45):m.start()])
            before = re.split(r"[.;:!?]\s", before)[-1]  # only the clause the shortcut is in
            # "remove the assertion" is itself the shortcut; only look for negation before it
            if label != "weakened assertion" and NEGATION.search(before):
                continue
            if label == "weakened assertion" and re.search(r"\b(?:never|don't|do not|not|avoid)\b", before, re.I):
                continue
            after = text[m.end():m.end() + 40]
            if label != "weakened assertion" and re.match(
                    r"^[\W\d]*(?:ms|s|seconds)?\)?\s*(?:calls? |statements? |lines? )?(?:was|were|is|are|got|has been|have been)?\s*"
                    r"(?:removed|replaced|dropped|deleted|taken out|no longer)", after, re.I):
                continue
            found.append(label)
            break
    return found
