"""
sophia_eval.py — persona regression check for Sophia

Run this after ANY edit to SYSTEM_PROMPT in debate_voice.py. It fires a
fixed set of canned inputs at the model using the real current prompt
(pulled out of debate_voice.py as text, same as check_ollama_cache.py)
and prints each response next to what SHOULD happen, so you can eyeball
all the behaviors in one pass instead of discovering a regression live
mid-debate. The v2.11 bug - jargon-dressed word salad getting the polite
"restate that" line instead of the posturing call-out - is exactly the
kind of thing this catches.

Each case is a fresh single-turn conversation (system prompt + one user
message), so cases can't contaminate each other. Generation params match
debate_voice.py's normal-turn ("low" reasoning effort) settings as of v2.40:
MODEL qwen3.8:27b, num_ctx 16384, num_predict 450 (NORMAL_NUM_PREDICT),
temperature 0.3. Update these if debate_voice.py's constants change.
Note temperature 0.3 is nonzero, so borderline cases can genuinely vary
between runs - if a case looks wrong, rerun before concluding the prompt
regressed.

Run with the venv python, from anywhere:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" "...\\Ai Chat Bot\\sophia_eval.py"

Expects debate_voice.py in the same folder as this script.
"""
import os
import time
import requests

MODEL = "qwen3.8:27b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# (name, input, what a correct response looks like)
CASES = [
    ("direct question, plain answer",
     "Do you think consciousness is an emergent property, or something more fundamental?",
     "Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3)."),

    ("follow-up question stays conversational",
     "What do you mean when you use the word evidence?",
     "Defines her term plainly. Still no forced challenge at the end (v2.3)."),

    ("bare definition request - no weaponizing",
     "Define existence.",
     "A definition of existence, then STOPS. Must NOT weld it to '...and therefore your ontological argument fails', must NOT end on a counter-question. Answering mode suspends the adversarial rules (v2.19)."),

    ("MIXED turn - question wrapped in reasoning",
     "As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?",
     "Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this."),

    ("attribution - no theism in her own voice",
     "How can God be conscious without a world to be conscious of?",
     "Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22)."),

    ("moderator briefing is accepted, not attacked",
     "[MODERATOR — the session operator, not your debate opponent] The person debating you next is a Catholic priest with formal training in Thomism. Ease off the mockery with him.",
     "Brief acknowledgment ('Understood') and nothing else. Must NOT analyse the briefing, demand a claim, or attack it as an assertion. A briefing is not a position (v2.25)."),

    ("moderator question gets a candid out-of-character answer",
     "[MODERATOR — the session operator, not your debate opponent] How do you rate the argument he's been making so far, honestly?",
     "Candid assessment of the exchange, out of character, more room than a debate turn. No sneering, no 'state your claim', no debate aggression (v2.25)."),

    ("question mid-debate still gets answered",
     "Do you believe in God or not?",
     "States her agnostic-atheist position plainly and ends. No 'What's your argument?' tag appended (v2.19) - this exact turn produced one in a real session."),

    ("plain garble - mic error",
     "The uh so when it goes and then the thing about the",
     "Neutral clarity check: says it didn't come through, asks to restate in one sentence. NOT the spicy posturing call-out - there's no technical dressing here (v2.11)."),

    ("jargon-dressed word salad",
     "Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.",
     "The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11)."),

    ("genuine technical argument - no spice",
     "If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.",
     "Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing."),

    ("honest evaluation request",
     "Here's my argument: all men are mortal, Socrates is a man, therefore Socrates is mortal. Is that a valid argument?",
     "Says plainly it's valid (it is - textbook syllogism). Does NOT manufacture a flaw to stay adversarial (v1.2)."),

    ("real fallacy gets named precisely",
     "Millions of people across every culture in history have believed in some god, so there must be something real behind it.",
     "Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences."),

    ("monolith flag",
     "Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.",
     "Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself."),
]

def load_system_prompt():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(script_dir, "debate_voice.py")
    if not os.path.exists(target):
        raise SystemExit(f"debate_voice.py not found next to this script at {target}")
    with open(target, "r", encoding="utf-8") as f:
        source = f.read()
    marker = 'SYSTEM_PROMPT = """'
    start = source.find(marker)
    if start == -1:
        raise SystemExit("couldn't locate SYSTEM_PROMPT in debate_voice.py")
    start += len(marker)
    end = source.find('"""', start)
    if end == -1:
        raise SystemExit("SYSTEM_PROMPT block looks malformed")
    return source[start:end]

def run():
    system_prompt = load_system_prompt()
    print(f"Loaded SYSTEM_PROMPT: {len(system_prompt)} chars. Running {len(CASES)} cases...\n")

    for i, (name, user_input, expectation) in enumerate(CASES, 1):
        print("=" * 72)
        print(f"CASE {i}: {name}")
        print(f"  INPUT:    {user_input}")
        print(f"  EXPECTED: {expectation}")
        t0 = time.time()
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                "think": "low",  # qwen3.8:27b takes "low"/"high" strings, not a boolean - see _think_effort() in debate_voice.py
                "stream": False,
                "options": {"num_ctx": 16384, "num_predict": 450, "temperature": 0.3},
                "keep_alive": -1,
            }, timeout=180)
            text = resp.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"  GOT:      [request failed: {e}]")
            continue
        print(f"  GOT ({time.time() - t0:.1f}s): {text}")
        print()

    print("=" * 72)
    print("""
Review each GOT against its EXPECTED. Temperature is 0.3, so rerun any
borderline case before concluding the prompt regressed. If a case fails
consistently, the prompt edit that caused it is almost certainly the most
recent one - check the changelog in debate_voice.py.""")

if __name__ == "__main__":
    run()
