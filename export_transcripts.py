"""
export_transcripts.py — turn Sophia's JSONL log into readable transcripts

Reads logs/sophia_log.jsonl (which already contains every word of every
exchange verbatim) and writes clean markdown transcripts to
logs/transcripts/ - one file per session, debates separated at each
'new' reset - so her answers can actually be reviewed for accuracy
without picking through raw JSONL.

Each turn shows a timestamp and the full text. Assistant turns get
flags appended when something went wrong mechanically (reply trimmed by
the token limit, empty reply, interrupted, model reloaded mid-session)
so mechanical failures aren't mistaken for reasoning failures during
review. At the end of each debate there's a blank "REVIEW NOTES" section
to jot accuracy verdicts into - those notes are exactly the raw material
for future prompt fixes.

Safe to re-run any time: it overwrites the transcript files from the log,
so notes should be kept in a copy or a separate file if you add them
directly. (Alternatively: paste review notes into the chat with Claude,
which can turn them into prompt fixes directly.)

Run with the venv python, from anywhere:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" "...\\Ai Chat Bot\\export_transcripts.py"
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE, "logs", "sophia_log.jsonl")
OUT_DIR = os.path.join(BASE, "logs", "transcripts")

def main():
    if not os.path.exists(LOG_PATH):
        raise SystemExit(f"No log found at {LOG_PATH} - run a session first.")
    os.makedirs(OUT_DIR, exist_ok=True)

    entries = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip a corrupt line rather than dying

    # Group by session id
    sessions = {}
    for e in entries:
        sessions.setdefault(e["session"], []).append(e)

    written = 0
    for session_id, evs in sessions.items():
        version = next((e.get("meta", {}).get("version") or e.get("v")
                        for e in evs if e["role"] == "session"), "?")
        lines = [f"# Sophia session {session_id} (v{version})", ""]
        debate_no = 1
        opened = False

        def open_debate():
            nonlocal opened
            lines.append(f"## Debate {debate_no}")
            lines.append("")
            opened = True

        def close_debate():
            nonlocal debate_no, opened
            if not opened:
                return
            lines.append("### REVIEW NOTES")
            lines.append("")
            lines.append("_(accuracy verdicts, misfires, anything worth fixing - fill in during review)_")
            lines.append("")
            debate_no += 1
            opened = False

        for e in evs:
            ts = e["ts"][11:19]
            m = e.get("meta", {})
            if e["role"] == "session":
                if "reset" in e["text"]:
                    close_debate()
                continue
            if not opened:
                open_debate()
            if e["role"] == "user":
                lines.append(f"**[{ts}] You:** {e['text']}")
                lines.append("")
            elif e["role"] == "assistant":
                flags = []
                if m.get("trimmed"):
                    flags.append("TRIMMED BY TOKEN LIMIT")
                if m.get("empty_reply"):
                    flags.append("EMPTY REPLY / FALLBACK LINE")
                if m.get("interrupted"):
                    flags.append("INTERRUPTED")
                load_ms = (m.get("ollama") or {}).get("load_ms")
                if load_ms and load_ms > 1000:
                    flags.append(f"MODEL RELOADED ({load_ms/1000:.1f}s)")
                flag_str = f"  _[{'; '.join(flags)}]_" if flags else ""
                lines.append(f"**[{ts}] Sophia:** {e['text']}{flag_str}")
                if m.get("trimmed_fragment"):
                    lines.append(f"  _(unspoken trimmed fragment: \"{m['trimmed_fragment']}\")_")
                lines.append("")
        close_debate()

        out_path = os.path.join(OUT_DIR, f"session_{session_id}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        written += 1

    print(f"Wrote {written} transcript file(s) to {OUT_DIR}")

if __name__ == "__main__":
    main()
