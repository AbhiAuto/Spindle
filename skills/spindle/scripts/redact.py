"""Remove secrets and identifying details from text before it is stored or shared.

Pattern based, so best effort: it catches the shapes it knows (keys, tokens,
passwords in key=value form, connection strings, private keys, e-mail
addresses, URLs, hosts, IP addresses). It cannot recognise a person's name or
free text. Memory changes are still reviewed in pull requests.
"""
import re

SCAN_LIMIT = 8000  # never run the patterns over huge blobs

# (label, pattern, replacement); order matters: specific shapes first
RULES = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.S),
     "[private key removed]"),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"), "[token removed]"),
    ("AWS key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[key removed]"),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "[key removed]"),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{30,})"), "[token removed]"),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}"), "[token removed]"),
    ("Slack webhook", re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/_-]+"), "[webhook removed]"),
    ("Stripe key", re.compile(r"\b[srp]k_(?:live|test)_[0-9A-Za-z]{10,}"), "[key removed]"),
    ("npm token", re.compile(r"\bnpm_[0-9A-Za-z]{30,}"), "[token removed]"),
    ("bearer token", re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,}", re.I), r"\1 [token removed]"),
    ("connection string", re.compile(
        r"\b(AccountKey|SharedAccessKey|SharedAccessSignature|Password|Pwd|User ID|Uid)\s*=\s*[^;\s'\"]+", re.I),
     r"\1=[removed]"),
    ("credentials in URL", re.compile(r"\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@", re.I), r"\1[credentials removed]@"),
    ("secret value", re.compile(
        r"(?i)\b((?:pass(?:word|wd|phrase|code)?|pwd|secret|token|api[-_ ]?key|apikey|client[-_ ]?secret|"
        r"access[-_ ]?key|private[-_ ]?key|auth|credential|otp|pin)\s*(?:is|was|=|:)\s*)"
        r"(['\"]?)(?![\[<$])([^\s'\",;]{4,})\2"), r"\1[removed]"),
    ("long random string", re.compile(
        r"\b(?=[A-Za-z0-9+/_=-]*[0-9])(?=[A-Za-z0-9+/_=-]*[A-Z])(?=[A-Za-z0-9+/_=-]*[a-z])[A-Za-z0-9+/_=-]{32,}\b"),
     "[token removed]"),
    ("e-mail address", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "[email removed]"),
    ("URL", re.compile(r"\bhttps?://[^\s)\]'\"]+", re.I), "[url removed]"),
    ("IP address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip removed]"),
    ("internal host", re.compile(
        r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|corp|local|lan|intranet|svc|cluster\.local)\b", re.I),
     "[host removed]"),
]
CONTROL = re.compile("[\\u0000-\\u0008\\u000b-\\u001f\\u007f\\u200b-\\u200f\\u2028\\u2029\\ufeff]")


def redact(text, keep_urls=False):
    """Return (clean_text, [labels of what was removed])."""
    if not text:
        return text, []
    t = CONTROL.sub(" ", text[:SCAN_LIMIT])
    found = []
    for label, rx, repl in RULES:
        if keep_urls and label in ("URL", "IP address", "internal host"):
            continue
        new = rx.sub(repl, t)
        if new != t:
            found.append(label)
            t = new
    return t, found


def scan_text(text, keep_urls=True):
    """Labels of secret-like things in text (URLs allowed by default: they are often fine in memory)."""
    return redact(text, keep_urls=keep_urls)[1]
