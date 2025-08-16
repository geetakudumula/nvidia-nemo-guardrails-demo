import csv
from types import SimpleNamespace
from nemoguardrails import LLMRails, RailsConfig

# -----------------------------
# Load CSV (ground-truth data)
# -----------------------------
words = []
with open("words.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        try:
            row["difficulty"] = int(row.get("difficulty", 5))
        except Exception:
            row["difficulty"] = 5
        words.append(row)

# sort hardest -> easiest
words.sort(key=lambda r: r["difficulty"], reverse=True)

ROUND_SIZE = 5
state = {"index": 0, "in_round": 0, "current": None, "correct": 0}


def _get_row(word: str):
    if not word:
        return None
    wl = word.strip().lower()
    for r in words:
        if r["word"].strip().lower() == wl:
            return r
    return None


# -----------------------------
# Actions (called from Colang v1)
# -----------------------------
def get_next_word():
    """Return next word for the round, or empty string if round finished."""
    if state["in_round"] >= ROUND_SIZE or state["index"] >= len(words):
        return ""
    w = words[state["index"]]["word"]
    state["current"] = w
    state["index"] += 1
    state["in_round"] += 1
    return w


def get_current():
    """Return the current word (or empty string)."""
    return state.get("current") or ""


def check_spelling(word, attempt):
    """Exact (case-insensitive) match check. Returns 'true' or 'false'."""
    ok = (attempt or "").strip().lower() == (word or "").strip().lower()
    if ok:
        state["correct"] += 1
    return "true" if ok else "false"


def get_definition(word):
    r = _get_row(word)
    return r["definition"] if r and r.get("definition") else "No definition found."


def get_origin(word):
    r = _get_row(word)
    return r["origin"] if r and r.get("origin") else "No origin found."


def get_sentence(word):
    r = _get_row(word)
    return r["sentence"] if r and r.get("sentence") else "No example available."


def get_progress():
    return f"Score this round: {state['correct']}/{state['in_round']}."


# -----------------------------
# Fully compatible Dummy LLM for NeMo Guardrails 0.15
# -----------------------------
class DummyLLM:
    """Return a LangChain-like LLMResult with generations + llm_output."""
    def __init__(self, text: str = ""):
        self._text = text

    def _result(self):
        gen = SimpleNamespace(text=self._text)
        # Guardrails expects these fields to exist
        return SimpleNamespace(generations=[[gen]], llm_output={})

    # async APIs Guardrails may use
    async def agenerate_prompt(self, *args, **kwargs):
        return self._result()

    async def agenerate(self, *args, **kwargs):
        return self._result()

    # sync fallbacks
    def generate_prompt(self, *args, **kwargs):
        return self._result()

    def generate(self, *args, **kwargs):
        return self._result()


# -----------------------------
# Wire up NeMo Guardrails (v1)
# -----------------------------
config = RailsConfig.from_path("rails")
rails = LLMRails(config, llm=DummyLLM())  # keep everything offline

for fn in [
    get_next_word,
    get_current,
    check_spelling,
    get_definition,
    get_origin,
    get_sentence,
    get_progress,
]:
    rails.register_action(fn)


# -----------------------------
# Response helpers
# -----------------------------
def extract_assistant_text(resp) -> str:
    """Try to pull assistant/bot text from various Guardrails return shapes."""
    if isinstance(resp, dict):
        # Common path
        if resp.get("content"):
            return resp["content"]

        # Messages list
        msgs = resp.get("messages") or resp.get("output", {}).get("messages", [])
        if isinstance(msgs, list) and msgs:
            parts = []
            for m in msgs:
                if isinstance(m, dict) and m.get("role") in ("assistant", "bot"):
                    txt = m.get("content") or m.get("text") or ""
                    if txt:
                        parts.append(txt)
            if parts:
                return "\n".join(parts)

        # Some builds emit a single message-like dict
        if resp.get("role") in ("assistant", "bot") and resp.get("content"):
            return resp["content"]

    # Fallback
    return ""


def run_local_engine(user: str) -> str:
    """Deterministic, no-LLM fallback that mirrors our flows."""
    u = (user or "").strip().lower()

    if u in ("start", "start quiz", "begin", "quiz me"):
        w = get_next_word()
        if not w:
            p = get_progress()
            return f"Round complete. {p}"
        return f"Okay! We'll do 5 words this round, hardest to easiest. Ready?\nSpell this word: {w}"

    if u == "definition":
        c = get_current()
        d = get_definition(c)
        return f"Definition: {d}"

    if u == "origin":
        c = get_current()
        o = get_origin(c)
        return f"Origin: {o}"

    if u == "sentence":
        c = get_current()
        s = get_sentence(c)
        return f"Example: {s}"

    if u == "next":
        n = get_next_word()
        if not n:
            p = get_progress()
            return f"Round complete. {p}"
        return f"Next word: {n}"

    if u in ("stop", "end", "finish"):
        p = get_progress()
        return f"Stopping the quiz. {p}"

    # Otherwise treat as spelling attempt
    c = get_current()
    if not c:
        # If user types a word before starting
        w = get_next_word()
        if not w:
            p = get_progress()
            return f"Round complete. {p}"
        # Re-run attempt logic on new word
        c = w

    ok = check_spelling(c, user)
    if ok == "true":
        n = get_next_word()
        if not n:
            p = get_progress()
            return f"✅ Correct!\nRound complete. {p}"
        return f"✅ Correct!\nNext word: {n}"
    else:
        return "❌ Not quite. Try again or ask for definition/origin/sentence."


# -----------------------------
# Tiny CLI loop
# -----------------------------
print(
    "Type: 'start' (or 'start quiz'), then 'definition'/'origin'/'sentence', "
    "type your spelling attempt, 'next', or 'stop'."
)

while True:
    user_in = input("You: ").strip()
    if not user_in:
        continue

    # Try Guardrails first
    try:
        resp = rails.generate(messages=[{"role": "user", "content": user_in}])
        tutor_text = extract_assistant_text(resp)
    except Exception:
        tutor_text = ""

    # Fallback to our local engine if Guardrails produced nothing visible
    if not tutor_text:
        tutor_text = run_local_engine(user_in)

    print("Tutor:", tutor_text or "[no response]")

    if ("Round complete" in tutor_text) or ("Stopping the quiz" in tutor_text):
        break

