"""
make_abliterated_model.py - build Sophia's model, qwen3.8-abliterated:27b.

It is huihui-ai's abliterated Qwen3.8 27B weights inside the STOCK Ollama
qwen3.8 template/renderer/parser. Why not just use the Hugging Face GGUF
directly: its own chat template returns an EMPTY reply whenever a system note
follows the user's turn, which Sophia does on every direct question (compare
run 20261016-2146 lost 42 of 92 turns to it).

What it does:
  1. downloads the abliterated weights if they aren't in Ollama yet (~17 GB)
  2. takes the template from qwen3.8:27b if you have it installed, otherwise
     from abliterated.modelfile shipped next to this script
  3. ollama create qwen3.8-abliterated:27b
Your stock qwen3.8:27b (if any) is not touched. Safe to run again.
"""

import os
import subprocess
import sys

STOCK = "qwen3.8:27b"
WEIGHTS = "hf.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:Q4_K_M"
NEW = "qwen3.8-abliterated:27b"
HERE = os.path.dirname(os.path.abspath(__file__))
SHIPPED = os.path.join(HERE, "abliterated.modelfile")


def run(args, show=False):
    if show:                                   # let ollama pull draw its own progress bar
        return subprocess.run(args).returncode, ""
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def installed(name):
    code, out = run(["ollama", "list"])
    return code == 0 and any(ln.split()[0].lower() == name.lower() for ln in out.splitlines()[1:] if ln.split())


def with_weights(modelfile_text):
    lines, done = [], False
    for ln in modelfile_text.splitlines():
        if ln.strip().upper().startswith("FROM "):
            if not done:
                lines.append(f"FROM {WEIGHTS}")
                done = True
            continue                           # drop any other FROM (e.g. a local blob path)
        lines.append(ln)
    if not done:
        lines.insert(0, f"FROM {WEIGHTS}")
    return "\n".join(lines) + "\n"


def main():
    if not installed(WEIGHTS):
        print(f"Downloading the abliterated weights ({WEIGHTS}, ~17 GB)...")
        code, _ = run(["ollama", "pull", WEIGHTS], show=True)
        if code != 0:
            print("Download failed - check your internet connection and run this again.")
            return 1
    if installed(STOCK):
        code, mf = run(["ollama", "show", STOCK, "--modelfile"])
        if code != 0:
            print(f"Couldn't read {STOCK}'s Modelfile:\n{mf}")
            return 1
        src = f"{STOCK} (installed)"
    elif os.path.exists(SHIPPED):
        mf = open(SHIPPED, encoding="utf-8").read()
        src = "abliterated.modelfile (shipped with Sophia)"
    else:
        print(f"Need either {STOCK} installed or abliterated.modelfile next to this script.")
        return 1
    path = os.path.join(HERE, "abliterated.local.modelfile")
    open(path, "w", encoding="utf-8").write(with_weights(mf))
    print(f"Template from: {src}")
    code, msg = run(["ollama", "create", NEW, "-f", path])
    print(msg.strip()[-400:])
    if code != 0:
        print("\n'ollama create' failed - see above. An old Ollama may not know the qwen3.8 "
              "renderer: update Ollama and run this again.")
        return 1
    print(f"\nCreated {NEW}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
