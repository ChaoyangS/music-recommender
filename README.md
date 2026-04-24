# Music Recommender — Agentic AI Edition

## Original Project

**Music Recommender Simulation** was a rule-based content filtering system built in Python. Given a user profile (favorite genre, mood, target energy, and acoustic preference), it scored every song in a 18-song CSV catalog using a weighted formula — genre match (+5), mood match (+4), energy closeness (+2), and acoustic bonus (+1) — then returned the top K results. The project demonstrated how real-world platforms like Spotify approximate "taste matching" without any machine learning, making the scoring logic fully transparent and inspectable.

---

## Title and Summary

**Music Recommender — Agentic AI Edition** extends the original rule-based recommender with a Claude-powered agent that accepts natural language requests and manages its own recommendation workflow. Instead of passing a hardcoded profile, a user can say *"I want something chill to study to"* and the agent will infer the right parameters, fetch recommendations, evaluate their quality, and retry with adjusted settings if the first attempt falls short — all automatically.

Every step of that process is visible. The agent prints Claude's planning text, each tool call with its inputs, the result of every tool, and a FIX notice whenever a retry is triggered. This makes the full PLAN → ACT → CHECK → FIX reasoning chain observable at runtime, not just the final answer.

This matters because it bridges the gap between brittle hand-tuned rules and a more natural, self-correcting AI assistant: the scoring engine stays deterministic and auditable, while Claude handles the fuzzy reasoning and quality judgment.

---

## Architecture Overview

```
User (natural language) ──► Agent (agent.py + Claude claude-opus-4-7)
                                │
                    ┌───────────┼───────────────┐
                    ▼           ▼               ▼
             browse_catalog  get_recommendations  evaluate_quality
                    │           │               │
                    └───────────┴───────────────┘
                                │
                        Retriever (recommender.py)
                                │
                          data/songs.csv
                          (18 songs · 10 features)
                                │
                         Ranked Results + Explanation ──► User
```

The system has four layers:

| Layer | File | Role |
|---|---|---|
| **Data** | `data/songs.csv` | 18 songs with genre, mood, energy, tempo, valence, danceability, acousticness |
| **Retriever** | `src/recommender.py` | `load_songs`, `score_song`, `recommend_songs` — pure scoring logic |
| **Agent** | `src/agent.py` | Claude agentic loop: PLAN → ACT → CHECK → FIX, up to 2 retries, observable steps |
| **Evaluation** | `evaluate.py` | 19-case harness — scoring engine + agent tools, pass/fail + confidence scores |

The `main.py` runner bypasses the agent and calls the retriever directly with three hardcoded profiles, useful for quick testing without API calls.

Human-in-the-loop testing lives in `tests/test_recommender.py` — a developer runs `pytest` and reviews failures before merging changes. The `evaluate.py` harness runs independently and checks end-to-end correctness across predefined profiles.

---

## Setup Instructions

### 1. Install dependencies

```bash
cd music-recommender
pip install -r requirements.txt
```

### 2. Add your Anthropic API key

Create a `.env` file in the project root (or the parent `music-recommander/` folder):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get your key at [console.anthropic.com](https://console.anthropic.com). Make sure your account has available credits.

### 3. Run the rule-based recommender (no API key needed)

```bash
python -m src.main
```

### 4. Run the AI agent with a natural language request

```bash
python src/agent.py "I want something chill to study to"
```

Or from the outer folder:

```bash
python /path/to/music-recommender/src/agent.py "I love relaxing jazz for a quiet evening"
```

### 5. Run the evaluation harness

```bash
python evaluate.py
```

Runs 19 predefined checks across the scoring engine and agent tool dispatcher and prints a pass/fail report with confidence scores. No API key needed.

### 6. Run unit tests

```bash
pytest
```

---

## Sample Interactions

### Example 1 — Study session request

**Input:**
```
python src/agent.py "I need focused background music for deep work sessions"
```

**Agent steps:**
```
────────────────────────────────────────────────
  Iteration 1
────────────────────────────────────────────────
  💭 PLAN: The user wants focused background music for deep work.
  💭 I'll look at the catalog first, then infer lofi + focused + low energy.

  ▶ PLAN  — browse catalog
    input : {}
    result: 18 songs in catalog

  ▶ ACT   — get recommendations
    input : {"favorite_genre": "lofi", "favorite_mood": "focused", "target_energy": 0.4, "likes_acoustic": true}
    result: 5 songs returned — top: "Focus Flow" (score=9.4)

  ▶ CHECK — evaluate quality
    input : {"recommendations": [...], "user_request": "I need focused background music..."}
    result: quality=good — ✔ no issues

[Agent] Done in 1 iteration(s).
```

**Output:**
> Here are my top picks for your deep work sessions:
> 1. **Focus Flow** by LoRoom (lofi, focused, 9.4) — perfect genre and mood match with low energy
> 2. **Midnight Coding** by LoRoom (lofi, chill, 8.4) — same artist, great for sustained concentration
> 3. **Library Rain** by Paper Lanterns (lofi, chill, 8.2) — soft acoustic texture ideal for reading
>
> All three are low-energy lofi tracks that minimize distraction while keeping you in a calm, alert state.

---

### Example 2 — High-energy workout request

**Input:**
```
python src/agent.py "I want energetic music to work out to!"
```

**Agent steps:**
```
────────────────────────────────────────────────
  Iteration 1
────────────────────────────────────────────────
  💭 PLAN: High energy workout request — pop or rock, intense mood, energy near 1.0.
  💭 No need to browse the catalog; I know what's available.

  ▶ ACT   — get recommendations
    input : {"favorite_genre": "pop", "favorite_mood": "intense", "target_energy": 0.9, "likes_acoustic": false}
    result: 5 songs returned — top: "Gym Hero" (score=11.0)

  ▶ CHECK — evaluate quality
    input : {"recommendations": [...], "user_request": "I want energetic music to work out to!"}
    result: quality=good — ✔ no issues

[Agent] Done in 1 iteration(s).
```

**Output:**
> For your workout, I recommend:
> 1. **Gym Hero** by Max Pulse (pop, intense, 11.0) — exact genre, mood, and energy match
> 2. **Storm Runner** by Voltline (rock, intense, 9.0) — driving rock energy at 152 BPM
> 3. **Sunrise City** by Neon Echo (pop, happy, 8.8) — upbeat pop to keep your pace up

---

### Example 3 — Late-night mood request with retry

**Input:**
```
python src/agent.py "Something atmospheric and moody for a late night drive"
```

**Agent steps:**
```
────────────────────────────────────────────────
  Iteration 1
────────────────────────────────────────────────
  💭 PLAN: Atmospheric and moody late-night drive — ambient or synthwave,
  💭 moody mood, medium energy around 0.5–0.7.

  ▶ ACT   — get recommendations
    input : {"favorite_genre": "ambient", "favorite_mood": "moody", "target_energy": 0.5}
    result: 5 songs returned — top: "Night Drive Loop" (score=6.2)

  ▶ CHECK — evaluate quality
    input : {"recommendations": [...], "user_request": "Something atmospheric and moody..."}
    result: quality=acceptable — ✘ Low genre diversity — all songs are ambient
    FIX   — adjusting parameters and retrying …

────────────────────────────────────────────────
  Iteration 2
────────────────────────────────────────────────
  💭 FIX: Diversity was low — switching genre to synthwave and raising energy slightly.

  ▶ ACT   — get recommendations
    input : {"favorite_genre": "synthwave", "favorite_mood": "moody", "target_energy": 0.7}
    result: 5 songs returned — top: "Night Drive Loop" (score=8.75)

  ▶ CHECK — evaluate quality
    input : {"recommendations": [...], "user_request": "Something atmospheric and moody..."}
    result: quality=good — ✔ no issues

[Agent] Done in 2 iteration(s).
```

**Output:**
> After adjusting for genre diversity, here are my late-night picks:
> 1. **Night Drive Loop** by Neon Echo (synthwave, moody) — neon-lit, cinematic energy
> 2. **Spacewalk Thoughts** by Orbit Bloom (ambient, chill) — ethereal and spacious
>
> The synthwave / ambient mix gives you that late-night atmosphere without getting too repetitive.

---

## Design Decisions

### Why keep the scoring engine separate from the agent?

`score_song()` in `recommender.py` is pure, deterministic Python — no API calls, no randomness. The agent calls it as a tool rather than asking Claude to score songs directly. This means the scoring logic is fully testable with `pytest`, costs nothing to run, and the results are reproducible. Claude's job is the fuzzy parts: interpreting natural language, evaluating quality, and deciding when to retry.

### Why a manual tool-use loop instead of a higher-level framework?

Using the raw Anthropic SDK loop (`response.content` → execute tools → append results → repeat) keeps the code visible and editable. There are no hidden abstractions. Every tool call and its result can be logged, inspected, or intercepted. The trade-off is more boilerplate compared to a framework like LangChain, but it makes the agent's behavior easier to understand and debug.

### Why prompt caching on the system prompt?

The system prompt is long and stable — it never changes between requests. Adding `cache_control: {"type": "ephemeral"}` tells Anthropic's API to cache it, so repeated calls (especially the CHECK → FIX retry loop) only charge input tokens for the new messages, not the prompt. This cuts costs roughly 3–5× on multi-iteration runs.

### Why make intermediate steps observable?

An agent that only shows its final answer is a black box — you can't tell whether it planned correctly, which tool it called first, or why it decided to retry. The verbose output in `run_agent` prints three distinct types of intermediate information: Claude's `💭` reasoning text (the planning and self-correction narration Claude writes before each tool call), `▶` step labels that map each tool call to its phase in the PLAN → ACT → CHECK → FIX loop, and a `FIX` notice that fires automatically when `evaluate_quality` returns "acceptable" or "poor." Together these let you follow the agent's decision-making chain step by step, catch bad parameter choices early, and verify that retries are actually improving the results. The trade-off is noisier terminal output; for production use, `verbose=False` silences all of it.

### Why a separate evaluation harness in addition to pytest?

`pytest` unit tests check that individual functions behave correctly in isolation — `score_song` adds the right points, `load_songs` parses floats, etc. They don't answer the question: *does the system actually recommend the right song for a real user profile?* `evaluate.py` fills that gap. It runs 12 realistic profiles (pop fan, jazz evening, folk acoustic, unknown genre, etc.) against the full 18-song catalog, verifies that the top-ranked song matches the expected genre and mood, checks that confidence scores fall in plausible ranges, and confirms that edge cases (k larger than catalog, zero-match genres) don't crash or return nonsense. Each case also reports a **confidence score** — top score ÷ 12.0 (the maximum possible) — so you can see at a glance whether a recommendation is a strong match or a weak fallback. The harness exits with code `1` if any check fails, which makes it easy to plug into CI alongside `pytest`.

### Why up to 2 retries and not more?

Each retry is an additional round-trip to the API, which adds latency and cost. In practice, one adjustment (e.g., switching from `ambient` to `synthwave`) is usually enough to move quality from "acceptable" to "good." A hard cap of 2 prevents runaway loops while still allowing meaningful self-correction.

### Trade-offs

| Decision | Benefit | Cost |
|---|---|---|
| 18-song catalog | Easy to reason about, fully auditable | Recommendations repeat quickly; limited diversity |
| Genre + mood as primary signals | Transparent, matches user mental model | Ignores tempo, valence, danceability in scoring |
| Single user profile (no history) | Simple to implement | Can't learn from past preferences |
| Claude claude-opus-4-7 | Best reasoning quality for agentic tasks | Higher cost per call vs. Haiku or Sonnet |

---

## Testing Summary

**42/42 unit tests passed · 19/19 evaluation checks passed.**

The project uses two complementary testing tools:

| Tool | Command | What it checks |
|---|---|---|
| `pytest` | `pytest` | Function-level correctness — scoring math, CSV parsing, sort order, OOP class |
| Evaluation harness | `python evaluate.py` | End-to-end correctness — right genre/mood surfaces for real profiles, confidence scores, edge cases |

### Evaluation harness results

```
Scoring engine : 12/12 passed  avg top-score=10.85  avg confidence=0.90
Agent tools    :  7/7  passed
Overall        : 19/19 passed  (100%)
```

Highlights from the 12 scoring cases:

| Case | Profile | Top song | Score | Confidence |
|---|---|---|---|---|
| SC-02 | Lofi / chill / acoustic | Midnight Coding | 11.96 | 1.00 |
| SC-05 | Folk / melancholic / acoustic | Sunset Wagon | 12.00 | 1.00 |
| SC-07 | Classical / dreamy / acoustic | Midnight Sonata | 12.00 | 1.00 |
| SC-11 | Unknown genre (edge case) | — | 5.48 | 0.46 |

SC-05 and SC-07 hit the maximum possible score of 12.0 (genre + mood + exact energy + acoustic bonus). SC-11 confirms the system degrades gracefully when the genre doesn't exist in the catalog — it still returns k results ranked by energy and mood proximity rather than crashing.

### What worked

- **`pytest` unit tests** caught the placeholder `Recommender.recommend()` returning unsorted results immediately. The tests enforce that the top result must match the expected genre and mood, which makes regressions visible.
- **The evaluation harness** confirmed that 8 out of 12 genre profiles achieve a confidence score ≥ 0.90, meaning the top recommendation uses at least 90% of the maximum possible score — a strong genre, mood, and energy match every time.
- **The agent's retry loop** worked correctly in the late-night scenario — the quality evaluator flagged low genre diversity on the first pass and Claude successfully adjusted the genre parameter on the retry.

### What didn't work / limitations

- **SC-11 (unknown genre) confidence = 0.46.** When the requested genre isn't in the catalog, the top score drops to ~5.5 because only mood and energy contribute. The system still returns results, but they are noticeably weaker matches.
- **18 songs is a very small catalog.** For niche requests (blues, reggae), there are too few songs for the diversity check to pass regardless of how the agent adjusts parameters.
- **The agent cannot learn across sessions.** Every run starts from scratch with no memory of what the user liked before.

### What I learned

- Writing the `_execute_tool()` dispatcher made clear how much of agent behavior is just routing: Claude decides *which* tool to call; Python decides *what to do* with that call. Keeping those responsibilities separate made each piece easier to test independently.
- The evaluation harness revealed something the unit tests missed: the confidence gap between a perfect match (1.00) and an unknown-genre fallback (0.46) is large enough to be meaningful. Unit tests verify correctness; the harness measures quality. Both are necessary.

---

## Reflection

See [model_card.md](model_card.md) for the full reflection, including limitations and biases, misuse considerations, testing surprises, and collaboration with AI.
