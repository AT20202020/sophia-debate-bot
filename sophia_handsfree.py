"""Hands-free mode for Sophia (v2.59) - she listens on her own.

Launched by choosing "2" in Start Sophia.bat, which runs
`debate_voice.py --handsfree`. debate_voice.py loads everything as usual
(Whisper, Kokoro, the model, the system prompt) and then, instead of the
push-to-talk console loop, hands its whole module to run() below. Nothing in
the push-to-talk path depends on this file.

A small window with three buttons:
  Start        she greets the room ("Hi, I'm Sophia. What's your claim about
               God?") and starts listening.
  Pause/Resume for side conversations. Paused = deaf; if she is mid-sentence
               she stops right away. Spacebar does the same.
  End          saves her memory summary of the debate (what 'new' does in
               push-to-talk) and resets for the next opponent.

TURN-TAKING RULES
  * You finish talking when there has been END_SILENCE_MS of quiet.
  * She only listens when the window says "Listening" (or "Hearing you..."
    once you've started). v2.61, Jeff's rule: from the moment your turn ends
    - through transcribing, thinking, speaking and DEAF_TAIL_MS after her
    last word - the mic is ignored. Anything said in that time is not heard;
    wait for "Listening" and say it again. She is never interrupted.

Speech detection is energy-based against a noise floor that adapts to the room,
and is AND-ed with webrtcvad if that package is installed. With a dedicated mic
and headphones (no speaker bleed) this is enough. Tuning knobs are the
constants just below.

Untested on real hardware at the time of writing - the constants will
probably need one round of adjustment.
"""

import collections
import queue
import threading
import time

import numpy as np
import sounddevice as sd

GREETING = "Hi, I'm Sophia. What's your claim about God?"

# v2.64: appended to her system prompt for the length of a hands-free debate,
# so she describes the setup correctly. Live 2026-10-09 she told the room "I
# can be interrupted at any time" - true of nothing in this mode.
HANDS_FREE_NOTE = """

THIS SESSION IS HANDS-FREE

You are running in hands-free mode in a room. You hear the room through a
microphone only while their screen says "Listening". You cannot be
interrupted: nothing said while you are thinking or speaking reaches you,
so if someone talks over you, it is lost and they need to say it again.
The operator can pause you for side conversations. If anyone asks how
this works, describe exactly that - never claim you can be interrupted.
"""

# --- Tuning knobs ------------------------------------------------------------
FRAME_MS = 20
FRAME = int(16000 * FRAME_MS / 1000)     # 320 samples per frame at 16kHz
START_WINDOW = 10                        # frames looked at to decide speech has started (200ms)
START_NEEDED = 7                         # ...of which this many must be voiced (~140ms of voice)
END_SILENCE_MS = 1200                    # quiet this long = you're done talking. Raise if she
                                         # jumps in while you're pausing to think; lower if she
                                         # feels slow to respond.
END_FRAMES = END_SILENCE_MS // FRAME_MS
PRE_ROLL_FRAMES = 15                     # 300ms kept from before speech started, so the first
                                         # word isn't clipped
KEEP_TRAILING_FRAMES = 10                # 200ms of the closing silence kept for Whisper
DEAF_TAIL_MS = 500                       # keep ignoring the mic this long after she stops
                                         # talking, so her last word's tail isn't caught
MAX_UTTERANCE_S = 90                     # force-end a turn this long (stuck-open safety net)
MIN_SPEECH_RMS = 0.010                   # absolute floor - never call anything quieter speech
SPEECH_FACTOR = 3.0                      # speech must be this many times louder than room noise

# Whole-turn transcripts that are just noise / filler, ignored instead of
# being sent to her. Includes Whisper's well-known phantom phrases.
FILLERS = {
    "", "um", "uh", "hmm", "mm", "mhm", "mm-hmm", "uh-huh", "ah", "oh",
    "yeah", "yep", "ok", "okay", "right", "so",
    "thank you", "thanks", "thanks for watching", "thank you for watching", "you",
}


def _norm(text):
    return "".join(c for c in text.lower() if c.isalnum() or c in " -").strip()


class HandsFree:
    def __init__(self, dv):
        self.dv = dv                     # the debate_voice module
        self.active = False
        self.saving = False
        self.session = 0
        self.paused = threading.Event()
        self.mic_q = queue.Queue()
        self.utter_q = queue.Queue()
        self.ui_q = queue.Queue()
        self.mic_stream = None
        self.controller_thread = None
        self.phase = "listening"         # listening | hearing
        self.busy = False                # she is replying (or greeting)
        self.turn_kind = None            # "greeting" | "reply"
        self.interrupt = threading.Event()
        self.cancel_reason = None        # "paused" | "ended"
        self.processing = False          # your turn ended; transcribing / handing to her
        self.level = 0.0
        self.threshold = MIN_SPEECH_RMS
        self.greet_audio = None
        self.deaf_until = 0.0
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(2)
            print("[hands-free: webrtcvad active alongside the energy detector]")
        except Exception:
            self.vad = None
            print("[hands-free: energy-based speech detection (webrtcvad-wheels not installed - optional)]")

    # --- setup ---------------------------------------------------------------
    def presynth_greeting(self):
        """Synthesize the greeting once at launch so Start plays it instantly."""
        try:
            chunks = [a for _, _, a in self.dv.tts_pipeline(
                self.dv.clean_for_speech(GREETING), voice=self.dv.VOICE, speed=self.dv.TTS_SPEED)]
            if chunks:
                self.greet_audio = self.dv._trim_silence(np.concatenate(chunks).astype(np.float32))
        except Exception as e:
            print(f"[hands-free: greeting pre-synthesis failed, will synthesize on Start - {e}]")

    # --- audio helpers -------------------------------------------------------
    def _mic_callback(self, indata, frames, time_info, status):
        if self.active and not self.paused.is_set() and not self._deaf():
            self.mic_q.put(indata[:, 0].copy())

    def _she_is_talking(self):
        return self.busy and (self.turn_kind == "greeting" or self._she_has_spoken())

    def _deaf(self):
        """v2.61: she listens only while the window says Listening / Hearing
        you - never while transcribing, thinking, talking, or just after."""
        return self.processing or self.busy or time.time() < self.deaf_until

    @staticmethod
    def _drain(q, task_done=False):
        while True:
            try:
                q.get_nowait()
                if task_done:
                    q.task_done()
            except queue.Empty:
                break

    def _hard_stop(self):
        """Silence her now and drop everything queued (Pause / End / withdraw)."""
        self.dv._audio_gen["n"] += 1
        self.dv.stop_audio.set()
        self._drain(self.dv.speech_queue, task_done=True)
        self._drain(self.dv.audio_queue, task_done=True)

    def _she_has_spoken(self):
        return self.dv.turn_timing["first_audio_time"] is not None

    def _audio_pending(self):
        return self.dv.speech_queue.unfinished_tasks > 0 or self.dv.audio_queue.unfinished_tasks > 0

    # --- listener: mic frames -> utterances ----------------------------------
    def _listener(self, sid):
        dv = self.dv
        floor = 0.003
        window = collections.deque(maxlen=START_WINDOW)
        pre = collections.deque(maxlen=PRE_ROLL_FRAMES)
        recording = False
        pending, pending_n, total_n, silence = [], 0, 0, 0
        parts, chunk_times = [], []

        def transcribe_pending(final):
            nonlocal pending, pending_n
            audio = np.concatenate(pending) if pending else np.zeros(0, np.float32)
            pending, pending_n = [], 0
            if len(audio) < dv.MIN_FINAL_CHUNK_SAMPLES:
                return
            t0 = time.time()
            text = dv._whisper_transcribe(audio, context=" ".join(parts))
            elapsed = time.time() - t0
            if text and parts and text.strip() == parts[-1].strip():
                print(f"[dropped echoed chunk: \"{text[:40]}...\"]")
                return
            chunk_times.append(round(elapsed, 2))
            print(f"[transcribe {'final chunk' if final else 'chunk'}: {elapsed:.2f}s]"
                  + (f' - "{text}"' if text else ""))
            if text:
                parts.append(text)

        while self.active and self.session == sid:
            if self._deaf() and not self.paused.is_set():
                # She's talking: throw away anything half-heard (a recording
                # that began just before her first word) and wait.
                if recording or pending:
                    recording = False
                    pending, pending_n, parts, chunk_times = [], 0, [], []
                    window.clear(); pre.clear()
                    self.phase = "listening"
                self._drain(self.mic_q)
                time.sleep(0.02)
                continue
            try:
                f = self.mic_q.get(timeout=0.1)
            except queue.Empty:
                continue
            if self.paused.is_set():
                recording = False
                pending, pending_n, parts, chunk_times = [], 0, [], []
                window.clear(); pre.clear()
                self.phase = "listening"
                continue

            rms = float(np.sqrt(np.mean(f * f))) if len(f) else 0.0
            thr = max(MIN_SPEECH_RMS, floor * SPEECH_FACTOR)
            self.level, self.threshold = rms, thr
            voiced = rms > thr
            if voiced and self.vad is not None and len(f) == FRAME:
                try:
                    voiced = self.vad.is_speech((np.clip(f, -1, 1) * 32767).astype(np.int16).tobytes(), 16000)
                except Exception:
                    pass
            if not voiced and not recording:
                # Room-noise floor: falls quickly, rises slowly.
                floor = 0.9 * floor + 0.1 * rms if rms < floor else 0.995 * floor + 0.005 * rms
                floor = min(max(floor, 0.0005), 0.03)

            if not recording:
                pre.append(f)
                window.append(voiced)
                if sum(window) >= START_NEEDED:
                    recording = True
                    pending = list(pre)
                    pending_n = total_n = sum(len(x) for x in pending)
                    silence, parts, chunk_times = 0, [], []
                    window.clear(); pre.clear()
                    self.phase = "hearing"
                continue

            pending.append(f)
            pending_n += len(f)
            total_n += len(f)
            silence = 0 if voiced else silence + 1
            if pending_n >= dv.CHUNK_SAMPLES and silence < END_FRAMES:
                transcribe_pending(final=False)
            if silence >= END_FRAMES or total_n >= MAX_UTTERANCE_S * 16000:
                self.processing = True   # deaf from here until she has answered
                drop = min(max(0, silence - KEEP_TRAILING_FRAMES), len(pending))
                if drop:
                    pending = pending[:-drop]
                transcribe_pending(final=True)
                recording = False
                self.phase = "listening"
                text = " ".join(parts).strip()
                self._drain(self.mic_q)  # nothing said while transcribing counts
                if self.paused.is_set() or not (self.active and self.session == sid):
                    self.processing = False
                    continue
                if _norm(text) in FILLERS:
                    if text:
                        print(f"[ignored filler: \"{text}\"]")
                    self.processing = False  # nothing for her to answer - back to listening
                    continue
                self.utter_q.put((text, {
                    "audio_seconds": round(total_n / 16000, 1),
                    "chunks": len(chunk_times),
                    "chunk_transcribe_s": chunk_times,
                    "chunk_texts": parts if len(parts) > 1 else None,
                    "gpu_transcription": bool(dv._whisper_server_available),
                }))

    # --- controller: utterances -> her replies --------------------------------
    def _wait_for_turn_end(self):
        while not self.interrupt.is_set() and self._audio_pending():
            time.sleep(0.05)
        self.deaf_until = time.time() + DEAF_TAIL_MS / 1000

    def _greet(self):
        dv = self.dv
        self.interrupt = threading.Event()
        self.cancel_reason = None
        self.turn_kind = "greeting"
        self.busy = True
        dv.stop_audio.clear()
        dv.turn_timing["first_audio_time"] = None
        if HANDS_FREE_NOTE not in dv.conversation[0]["content"]:
            dv.conversation[0]["content"] += HANDS_FREE_NOTE
        dv.conversation.append({"role": "assistant", "content": GREETING})
        dv.log_event("assistant", GREETING, greeting=True, hands_free=True)
        # v2.64: warm the model on exactly what the first turn will send,
        # while the greeting plays and they think. Launch priming has been
        # unreliable (first turn 7.1s on 2026-10-09); the post-End re-prime
        # worked every time (~0.9s first turns), and this is the same call.
        threading.Thread(target=dv.prime_model, args=(list(dv.conversation), "start"),
                         daemon=True).start()
        print(f"Sophia: {GREETING}")
        self.ui_q.put(("sophia", GREETING))
        if self.greet_audio is not None:
            dv.audio_queue.put((self.greet_audio, True))
        else:
            dv.speech_queue.put((GREETING, True))
        self._wait_for_turn_end()
        self.busy = False

    def _unwind_turn(self, text):
        """Remove a reply she never spoke (and the turn it answered) from context."""
        conv = self.dv.conversation
        if conv and conv[-1]["role"] == "assistant":
            conv.pop()
        if conv and conv[-1]["role"] == "user" and conv[-1]["content"] == text:
            conv.pop()

    def _controller(self, sid):
        dv = self.dv
        self._greet()
        while self.active and self.session == sid:
            try:
                text, meta = self.utter_q.get(timeout=0.1)
            except queue.Empty:
                continue
            if self.paused.is_set():
                self.processing = False
                continue
            # Anything else already waiting becomes part of this turn.
            while True:
                try:
                    more, _ = self.utter_q.get_nowait()
                    text = f"{text} {more}"
                except queue.Empty:
                    break
            text = text.strip()
            if not text:
                self.processing = False
                continue

            print(f"You: {text}")
            dv.log_event("user", text, hands_free=True, **meta)
            self.ui_q.put(("you", text))

            self.interrupt = threading.Event()
            self.cancel_reason = None
            self.turn_kind = "reply"
            dv.stop_audio.clear()
            dv.turn_timing["first_audio_time"] = None
            self.busy = True
            self.processing = False   # busy now keeps her deaf
            reply = dv.get_response_streaming(text, interrupt_event=self.interrupt)
            self._wait_for_turn_end()

            if self.interrupt.is_set():
                self._hard_stop()
                if not self._she_has_spoken():
                    self._unwind_turn(text)
                    dv.log_event("session", "reply withdrawn before she spoke",
                                 reason=self.cancel_reason, hands_free=True)
                else:
                    self.ui_q.put(("sophia", reply + "  [stopped]"))
            else:
                self.ui_q.put(("sophia", reply))
            if not self._she_has_spoken():
                self.deaf_until = time.time() + DEAF_TAIL_MS / 1000
            self.busy = False

    # --- buttons --------------------------------------------------------------
    def start(self):
        if self.active or self.saving:
            return
        self.session += 1
        sid = self.session
        self.paused.clear()
        self._drain(self.mic_q)
        self._drain(self.utter_q)
        self.processing = False
        self.phase = "listening"
        try:
            self.mic_stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                             blocksize=FRAME, callback=self._mic_callback)
            self.mic_stream.start()
        except Exception as e:
            self.ui_q.put(("info", f"Could not open the microphone: {e}"))
            print(f"[hands-free: could not open microphone - {e}]")
            return
        self.active = True
        self.dv.log_event("session", "hands-free debate started")
        self.ui_q.put(("info", "--- Debate started ---"))
        threading.Thread(target=self._listener, args=(sid,), daemon=True).start()
        self.controller_thread = threading.Thread(target=self._controller, args=(sid,), daemon=True)
        self.controller_thread.start()

    def toggle_pause(self):
        if not self.active:
            return
        if self.paused.is_set():
            self._drain(self.mic_q)
            self.paused.clear()
            self.dv.log_event("session", "hands-free resumed")
            self.ui_q.put(("info", "--- Resumed ---"))
        else:
            self.paused.set()
            self._drain(self.utter_q)
            self.processing = False
            if self.busy:
                self.cancel_reason = "paused"
                self.interrupt.set()
                self._hard_stop()
            self.dv.log_event("session", "hands-free paused")
            self.ui_q.put(("info", "--- Paused ---"))

    def end(self):
        if not self.active:
            return
        self.active = False
        self.session += 1
        self.paused.clear()
        if self.busy:
            self.cancel_reason = "ended"
            self.interrupt.set()
            self._hard_stop()
        try:
            self.mic_stream.stop()
            self.mic_stream.close()
        except Exception:
            pass
        self._drain(self.utter_q)
        self.processing = False
        self.saving = True
        self.ui_q.put(("info", "--- Debate ended - saving to memory ---"))
        threading.Thread(target=self._save_and_reset, daemon=True).start()

    def _save_and_reset(self):
        dv = self.dv
        try:
            # Let the in-flight turn (if any) finish unwinding first, so it
            # can't append to the fresh conversation below.
            if self.controller_thread is not None:
                self.controller_thread.join(timeout=30)
            dv.summarize_and_save_memory(dv.conversation)
            dv.conversation = [{"role": "system",
                                "content": dv.SYSTEM_PROMPT + dv.load_memory_context()}]
            dv.log_event("session", "hands-free debate ended (context cleared)")
            dv.prime_model(list(dv.conversation), "reset")
        except Exception as e:
            print(f"[hands-free: error while saving/resetting - {e}]")
        finally:
            self.saving = False
            self.ui_q.put(("info", "Ready for the next opponent - press Start."))

    # --- status for the window --------------------------------------------------
    def status(self):
        if self.saving:
            return "Saving the debate to memory...", "#888888"
        if not self.active:
            return "Press Start to begin", "#888888"
        if self.paused.is_set():
            return "Paused - she can't hear you (Space or Resume)", "#d08a00"
        if self._she_is_talking():
            return "Sophia is speaking - not listening", "#7a4fd1"
        if self.busy or self.processing:
            return "Sophia is thinking - not listening", "#2f7dd1"
        if time.time() < self.deaf_until:
            return "Sophia is speaking - not listening", "#7a4fd1"
        if self.phase == "hearing":
            return "Hearing you...", "#1f9d55"
        return "Listening", "#1f9d55"


def run(dv):
    """Entry point, called from the bottom of debate_voice.py."""
    try:
        import tkinter as tk
        from tkinter import scrolledtext
    except Exception as e:
        print(f"\n[hands-free mode needs tkinter, which isn't available in this Python: {e}]")
        print("[Re-run Python's installer, choose Modify, and tick 'tcl/tk and IDLE'.]")
        return

    hf = HandsFree(dv)
    print("Preparing greeting...")
    hf.presynth_greeting()
    print("\nHands-free mode - use the Sophia window. (This console shows the details.)")

    root = tk.Tk()
    root.title(f"Sophia v{dv.VERSION} - hands-free")
    root.geometry("560x480")
    root.minsize(420, 360)

    top = tk.Frame(root, padx=12, pady=10)
    top.pack(fill="x")
    dot = tk.Canvas(top, width=18, height=18, highlightthickness=0)
    dot.pack(side="left")
    dot_id = dot.create_oval(2, 2, 16, 16, fill="#888888", outline="")
    status_lbl = tk.Label(top, text="", font=("Segoe UI", 14, "bold"), anchor="w")
    status_lbl.pack(side="left", padx=8, fill="x", expand=True)

    btns = tk.Frame(root, padx=12)
    btns.pack(fill="x")
    bstyle = dict(font=("Segoe UI", 12), width=10, takefocus=0)
    start_btn = tk.Button(btns, text="Start", command=hf.start, **bstyle)
    pause_btn = tk.Button(btns, text="Pause", command=hf.toggle_pause, **bstyle)
    end_btn = tk.Button(btns, text="End", command=hf.end, **bstyle)
    for b in (start_btn, pause_btn, end_btn):
        b.pack(side="left", padx=(0, 8), pady=6)

    meter = tk.Canvas(root, height=10, highlightthickness=0, bg="#e6e6e6")
    meter.pack(fill="x", padx=12, pady=(4, 2))
    tk.Label(root, text="mic level (the line is the speech threshold)   |   Space = pause/resume",
             font=("Segoe UI", 8), fg="#777777").pack(anchor="w", padx=12)

    log = scrolledtext.ScrolledText(root, wrap="word", font=("Segoe UI", 11),
                                    state="disabled", takefocus=0, padx=8, pady=6)
    log.pack(fill="both", expand=True, padx=12, pady=(6, 12))
    log.tag_config("you", foreground="#1f6f3f")
    log.tag_config("sophia", foreground="#4b2a8f")
    log.tag_config("info", foreground="#888888")

    def add_line(kind, text):
        label = {"you": "You: ", "sophia": "Sophia: ", "info": ""}[kind]
        log.configure(state="normal")
        log.insert("end", label + text + "\n\n", kind)
        log.configure(state="disabled")
        log.see("end")

    def level_x(v, width):
        db = 20 * np.log10(max(v, 1e-5))          # -100..0 dBFS
        return int(max(0.0, min(1.0, (db + 60) / 60)) * width)

    closing = {"on": False}

    def poll():
        while True:
            try:
                add_line(*hf.ui_q.get_nowait())
            except queue.Empty:
                break
        text, color = hf.status()
        status_lbl.config(text=text)
        dot.itemconfig(dot_id, fill=color)
        start_btn.config(state="normal" if not hf.active and not hf.saving else "disabled")
        pause_btn.config(state="normal" if hf.active else "disabled",
                         text="Resume" if hf.paused.is_set() else "Pause")
        end_btn.config(state="normal" if hf.active else "disabled")
        w = meter.winfo_width()
        meter.delete("all")
        if hf.active and not hf.paused.is_set():
            meter.create_rectangle(0, 0, level_x(hf.level, w), 10, fill="#1f9d55", outline="")
            tx = level_x(hf.threshold, w)
            meter.create_line(tx, 0, tx, 10, fill="#cc3333", width=2)
        if closing["on"] and not hf.active and not hf.saving:
            root.destroy()
            return
        root.after(100, poll)

    def on_space(event):
        hf.toggle_pause()
        return "break"

    def on_close():
        if closing["on"]:
            return
        closing["on"] = True
        if hf.active:
            hf.end()          # saves memory first; poll() closes the window when done

    root.bind_all("<space>", on_space)
    root.protocol("WM_DELETE_WINDOW", on_close)
    add_line("info", "Press Start. She'll greet the room and start listening.\n"
                     "Pause for side conversations, End when the debate is over.")
    poll()
    root.mainloop()
    print("Goodbye.")
