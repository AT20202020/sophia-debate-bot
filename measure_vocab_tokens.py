"""
measure_vocab_tokens.py - does Whisper's prompt fit its 223-token window?

faster-whisper keeps only the LAST 223 tokens of initial_prompt (max_length 448
// 2 - 1) and silently drops the front. _whisper_transcribe() sends
"<last 150 chars of this utterance> <DOMAIN_VOCAB_PROMPT><topic pack if live>",
so anything over the limit eats the rolling context first, then the start of
the vocab list.

Measures four cases: base list, base + historicity pack, each with and without
150 chars of context. The worst case (base + pack + context) is the one that
must fit.

Reads DOMAIN_VOCAB_PROMPT out of debate_voice.py as text (does NOT import the
bot, which would load Kokoro and open audio). Uses the real tokenizer for the
bot's WHISPER_MODEL_SIZE.

Exit codes: 0 = worst case fits; 2 = worst case over (Run v2.57 Checks.bat
stops before the eval); anything else = the script itself errored.
Run: <venv python> measure_vocab_tokens.py
"""
import os
import sys

from faster_whisper import WhisperModel

LIMIT = 223
CONTEXT_CHARS = 150  # matches context[-150:] in _whisper_transcribe()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from historicity_reference import VOCAB_PACK  # noqa: E402

src = open(os.path.join(HERE, "debate_voice.py"), encoding="utf-8").read()
start = src.index("DOMAIN_VOCAB_PROMPT = (")
end = src.index("\n)\n", start) + 3
ns = {}
exec(src[start:end], ns)
base = ns["DOMAIN_VOCAB_PROMPT"]
size_line = next(l for l in src.splitlines() if l.startswith("WHISPER_MODEL_SIZE"))
size = size_line.split("=")[1].split("#")[0].strip().strip('"\'')

print(f"Loading tokenizer for {size}...")
tok = WhisperModel(size, device="cpu", compute_type="int8").hf_tokenizer


def count(text):
    # faster-whisper encodes " " + prompt.strip()
    return len(tok.encode(" " + text.strip(), add_special_tokens=False).ids)


# Ordinary mid-debate speech, as prepended on every chunk after the first.
context = ("so what you are saying is that the historians who wrote after the "
           "fact are enough to establish that he existed at all, and I think "
           "that is a stretch")[-CONTEXT_CHARS:]

with_pack = base + " " + VOCAB_PACK
rows = [
    ("base list", base),
    ("base + context", context + " " + base),
    ("base + historicity pack", with_pack),
    ("base + pack + context (WORST)", context + " " + with_pack),
]
print(f"\nwindow: {LIMIT} tokens\n")
worst = 0
for label, text in rows:
    n = count(text)
    worst = n
    flag = "fits" if n <= LIMIT else f"OVER by {n - LIMIT}"
    print(f"  {label:32s} {n:4d} tokens  {flag}")

print()
if worst > LIMIT:
    print(f"OVER: the worst case loses {worst - LIMIT} tokens from the front "
          "(context first). Trim the base list or the pack.")
    raise SystemExit(2)
print(f"FITS: {LIMIT - worst} tokens to spare in the worst case.")
