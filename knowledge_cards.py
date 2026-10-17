"""
knowledge_cards.py - generic argument-card engine for Sophia (v2.69).

A Topic is: a CORE block (injected once, the first time the topic's TRIGGER
fires) plus a folder of .md cards (knowledge/<folder>/), each with `title:` and
`triggers:` in a --- header. Matching cards are injected turn by turn, each once,
only while the topic is live. Same design as historicity_reference.py (v2.66),
which predates this engine and still runs its own copy of the logic; it can move
onto this engine later without changing behavior.

Used by morality_reference.py. Blocks are inserted as system messages just
before the latest user turn, so the cached prefix above them is untouched.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def _phrase_regex(phrase):
    body = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)


def normalize(text):
    # Whisper sometimes emits curly apostrophes.
    return (text or "").replace("’", "'").replace("‘", "'")


class Topic:
    def __init__(self, name, marker, trigger, core, folder,
                 max_new_per_turn=2, max_per_debate=6, max_card_chars=2400):
        self.name = name
        self.marker = marker
        self.trigger = trigger
        self.core = core
        self.cards_dir = os.path.join(HERE, "knowledge", folder)
        self.card_prefix = f"REFERENCE CARD ({name}): "
        self.max_new_per_turn = max_new_per_turn
        self.max_per_debate = max_per_debate
        self.max_card_chars = max_card_chars
        self._cache = {"sig": None, "cards": []}

    # -- cards ---------------------------------------------------------------
    def _parse(self, path):
        with open(path, encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
        parts = text.split("---", 2)
        if not text.lstrip().startswith("---") or len(parts) < 3:
            raise ValueError("missing the --- header block")
        fields = {}
        for line in parts[1].strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip().lower()] = v.strip()
        body = parts[2].strip()
        title = fields.get("title", "")
        triggers = [t.strip().lower() for t in fields.get("triggers", "").split(",") if t.strip()]
        if not title:
            raise ValueError("no title:")
        if not triggers:
            raise ValueError("no triggers:")
        if not body:
            raise ValueError("empty body")
        return {"file": os.path.basename(path), "title": title, "triggers": triggers,
                "regexes": [(t, _phrase_regex(t)) for t in triggers], "body": body,
                "content": f"{self.card_prefix}{title}\n{body}"}

    def _files(self):
        if not os.path.isdir(self.cards_dir):
            return []
        return sorted(os.path.join(self.cards_dir, n) for n in os.listdir(self.cards_dir)
                      if n.lower().endswith(".md") and not n.startswith("_")
                      and n.lower() != "readme.md")

    def load_cards(self, strict=False):
        files = self._files()
        sig = tuple((p, os.path.getmtime(p)) for p in files)
        if sig == self._cache["sig"]:
            return self._cache["cards"]
        cards = []
        for p in files:
            try:
                cards.append(self._parse(p))
            except (ValueError, OSError, UnicodeDecodeError) as e:
                if strict:
                    raise ValueError(f"{os.path.basename(p)}: {e}") from e
                print(f"[{self.name} card skipped: {os.path.basename(p)} - {e}]", flush=True)
        self._cache["sig"], self._cache["cards"] = sig, cards
        return cards

    def match_cards(self, text):
        text = normalize(text)
        scored = []
        for c in self.load_cards():
            hits = [t for t, rx in c["regexes"] if rx.search(text)]
            if hits:
                scored.append((-len(hits), -max(len(h) for h in hits), c["file"], c))
        scored.sort(key=lambda s: s[:3])
        return [s[3] for s in scored]

    # -- injection -----------------------------------------------------------
    def is_live(self, history):
        return any(m.get("role") == "system" and self.marker in (m.get("content") or "")
                   for m in history)

    def inject_if_relevant(self, history, user_text):
        """Insert CORE (once) and matching cards (each once). Returns labels."""
        if not user_text:
            return []
        contents = [m.get("content") or "" for m in history if m.get("role") == "system"]
        core_present = any(self.marker in c for c in contents)
        titles = {c[len(self.card_prefix):].split("\n", 1)[0] for c in contents
                  if c.startswith(self.card_prefix)}
        new, labels = [], []
        if not core_present:
            if not self.trigger.search(normalize(user_text)):
                return []
            new.append(self.core)
            labels.append("core")
        room = self.max_per_debate - len(titles)
        added = 0
        for c in self.match_cards(user_text):
            if room <= 0 or added >= self.max_new_per_turn:
                break
            if c["title"] in titles:
                continue
            new.append(c["content"])
            labels.append(c["title"])
            room -= 1
            added += 1
        if not new:
            return []
        at = len(history) - 1 if history and history[-1].get("role") == "user" else len(history)
        for i, content in enumerate(new):
            history.insert(at + i, {"role": "system", "content": content})
        return labels

    # -- self-test helpers -----------------------------------------------------
    def check_cards(self, check):
        try:
            cards = self.load_cards(strict=True)
        except ValueError as e:
            check(False, f"{self.name} card parse error - {e}")
            return []
        check(len(cards) > 0, f"{len(cards)} {self.name} cards loaded from {self.cards_dir}")
        seen = set()
        for c in cards:
            check(len(c["body"]) <= self.max_card_chars,
                  f"{c['file']}: {len(c['body']):,} chars (limit {self.max_card_chars:,})")
            check(c["title"] not in seen, f"{c['file']}: title is unique")
            seen.add(c["title"])
        return cards


def fixed_instruction_texts():
    """VERDICT/STEELMAN fixed text from debate_voice.py beside this file, for
    self-tests: those turns must never inject anything (verdict pop()s 2)."""
    out = {}
    dv = os.path.join(HERE, "debate_voice.py")
    if not os.path.exists(dv):
        return out
    src = open(dv, encoding="utf-8").read()
    for name in ("VERDICT_INSTRUCTION", "STEELMAN_INSTRUCTION"):
        m = re.search(name + r"\s*=\s*\(((?:\s*\"[^\"]*\")+)\s*\)", src)
        if m:
            out[name] = "".join(re.findall(r"\"([^\"]*)\"", m.group(1)))
    return out
