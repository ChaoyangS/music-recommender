# Video Walkthrough Script — Music Recommender Agentic AI Edition
**Target length:** 5–7 minutes

---

## [0:00–0:40] INTRO — What this project is

**Screen:** project folder open in IDE, README visible

> "Hi — in this walkthrough I'm going to show you a music recommendation system I built
> in Python using the Anthropic Claude API.
>
> The project started as a simple rule-based recommender: you give it a genre, a mood,
> and a target energy level, and it scores every song in a catalog and returns the best
> matches. That part required no AI at all — just math.
>
> Then I extended it with an agentic workflow: instead of passing a structured profile,
> you can say something like 'I need something chill to study to' in plain English,
> and a Claude-powered agent figures out the right parameters, fetches recommendations,
> evaluates whether they're good, and retries with adjusted settings if they're not.
>
> I'll walk through the full system end to end — three live demos, the evaluation
> harness, and what I learned building it."

---

## [0:40–1:20] SYSTEM OVERVIEW — Architecture in 30 seconds

**Screen:** open `mermaid.js` or show the architecture diagram from the README

> "Here's how the pieces fit together.
>
> At the bottom is the data layer — a CSV of 18 songs, each with genre, mood, energy,
> acousticness, and a few other features.
>
> Above that is the retriever: pure Python functions in `recommender.py` that load
> the catalog, score every song against a user profile, and return the top K.
> No API calls. Completely deterministic and testable.
>
> On top of that sits the agent in `agent.py`. It uses Claude's tool-use API to run
> a four-phase loop: PLAN — infer preferences from natural language. ACT — call the
> scoring engine. CHECK — evaluate the quality of the results. FIX — adjust and retry
> if the quality isn't good enough. Up to two retries are allowed.
>
> The key design decision was to keep the scoring engine separate from the agent.
> Claude does the fuzzy reasoning; Python does the arithmetic. That separation made
> everything easier to test."

---

## [1:20–2:30] DEMO 1 — Happy path: study session

**Screen:** terminal, project root

**Type and run:**
```
python src/agent.py "I need focused background music for deep work sessions"
```

> "Let's start with a straightforward request — focused music for deep work.
>
> Watch the output as it runs. You can see the iteration label at the top, then
> Claude's planning text — that's the actual reasoning Claude wrote before deciding
> what to do. It's inferring lofi, focused mood, low energy.
>
> Then the tool calls: first it browses the catalog to see what's available, then
> calls get_recommendations with those inferred parameters, then calls evaluate_quality.
>
> Quality comes back as 'good' with no issues — so the agent stops and writes
> the final explanation.
>
> The top result is Focus Flow by LoRoom — a lofi, focused track with a score of 9.4
> out of a maximum possible 12. That's a genre match, a mood match, and close
> energy — exactly what the request asked for.
>
> One thing I want to point out: the reasoning text you see with the 💭 symbol was
> hidden in the original version of the agent. Claude was planning internally but
> the output only showed tool call names. I added code to surface those text blocks
> so the full decision chain is visible — not just the final answer."

---

## [2:30–3:20] DEMO 2 — Fast path: workout

**Screen:** same terminal

**Type and run:**
```
python src/agent.py "I want energetic music to work out to!"
```

> "Second demo — a high-energy workout request. This one is faster because the
> request is unambiguous.
>
> Notice Claude skips the catalog browse this time — it already knows what's
> available from the system prompt and goes straight to get_recommendations
> with pop, intense mood, energy near 0.9.
>
> Gym Hero by Max Pulse comes back at the top with a score of 11 out of 12.
> Quality is immediately good, so the agent finishes in one iteration.
>
> This shows the agent making a judgment call — browse_catalog is available as a tool
> but Claude chose not to use it here because the request was clear enough.
> That's the kind of decision a rigid workflow can't make."

---

## [3:20–4:30] DEMO 3 — Retry behavior: late-night drive

**Screen:** same terminal

**Type and run:**
```
python src/agent.py "Something atmospheric and moody for a late night drive"
```

> "This third demo is the most interesting one because it shows the CHECK and FIX
> phases in action.
>
> The request is vague — 'atmospheric and moody' could mean several things.
> Claude starts with ambient genre and moody mood.
>
> Watch what happens after the first set of recommendations: the quality check
> flags low genre diversity — all five songs came back as ambient.
> You can see the FIX notice print automatically.
>
> In the second iteration, Claude adjusts: it switches to synthwave and raises
> the energy slightly. The new top result is Night Drive Loop by Neon Echo —
> a synthwave track — and now the recommendations include a mix of genres.
> Quality comes back good.
>
> This is the self-correction loop working as designed. The agent didn't just
> accept the first answer — it noticed the problem, made a targeted adjustment,
> and verified the improvement. Without the quality evaluator, that first
> ambient-heavy result would have been the final answer."

---

## [4:30–5:20] EVALUATION HARNESS — Reliability check

**Screen:** terminal

**Type and run:**
```
python evaluate.py
```

> "Beyond the AI agent, I also built an evaluation harness that tests the system
> on 19 predefined cases — no API key needed, everything runs locally.
>
> You can see it working through 12 scoring engine cases: pop fan, lofi study,
> jazz evening, folk acoustic, classical dreamy — each one checks that the right
> song surfaces, the score meets a minimum threshold, results are sorted correctly,
> and no scores go negative.
>
> Scroll down to the summary: 12 out of 12 scoring cases passed, 7 out of 7
> agent tool checks passed. Average confidence is 0.90 — meaning on average the
> top recommendation uses 90% of the maximum possible score.
>
> The interesting case is SC-11 — unknown genre. When I request a genre that
> doesn't exist in the catalog, confidence drops to 0.46. The system doesn't crash,
> it still returns five songs ranked by energy and mood, but the quality is noticeably
> weaker. That's the honest failure mode, and having it quantified is more useful
> than just knowing it 'might not work.'"

---

## [5:20–6:10] WHAT I LEARNED

**Screen:** README open to Reflection section, or face-to-camera

> "A few things surprised me building this.
>
> First — the gap between a passing test suite and a working system is real.
> The original Recommender class had a placeholder that returned songs in
> insertion order, not by score. Both starter tests passed anyway because the
> fixture happened to add the pop song first. It took writing a second test
> with a different profile to catch it. Tests are only as good as the assumptions
> in the fixtures.
>
> Second — the self-correction loop changed how I think about AI reliability.
> A single model call can be wrong. A model that checks its own output and
> adjusts is meaningfully more robust. The quality evaluator is simple — it
> just counts genres and checks average scores — but it caught a real problem
> in the late-night demo. Even a basic feedback signal makes the system better.
>
> Third — separating language model reasoning from deterministic computation
> made everything cleaner. Claude is good at interpreting 'something for a
> late-night drive.' Python is good at arithmetic. Mixing those two things
> in the same function would have made both harder to test and harder to trust."

---

## [6:10–6:50] REFLECTION — What this says about me as an AI engineer

**Screen:** face-to-camera or code editor

> "This project reflects how I think about building AI systems.
>
> I didn't treat Claude as a black box that produces answers — I treated it as
> one component in a larger system where each part has a clear responsibility.
> The scoring engine is deterministic and tested. The agent loop is bounded
> and observable. The evaluation harness makes quality measurable, not just
> qualitative.
>
> That instinct — to make AI behavior visible, testable, and correctable —
> is what I want to carry into every AI system I build. A model that explains
> its reasoning at every step is more trustworthy than one that just returns
> a result. A system with a feedback loop is more reliable than one that accepts
> the first answer. And a confidence score is more honest than a thumbs-up.
>
> I'm still learning, but I think the right question when building with AI isn't
> 'what can the model do?' — it's 'how do I know when it's working, and what
> happens when it's not?'"

---

## [6:50–7:00] CLOSE

**Screen:** terminal with final evaluate.py output visible

> "Thanks for watching. The full source code, README, and evaluation script
> are all in the repo. If you want to run it yourself, check the setup
> instructions — it's just pip install and a .env file with your API key."

---

## Quick reference — commands used in order

```bash
# Demo 1 — happy path
python src/agent.py "I need focused background music for deep work sessions"

# Demo 2 — fast path
python src/agent.py "I want energetic music to work out to!"

# Demo 3 — retry behavior
python src/agent.py "Something atmospheric and moody for a late night drive"

# Evaluation harness
python evaluate.py
```

## Tips for recording

- Run each command once before recording so the `.env` and imports are warm.
- Keep the terminal font at 16pt+ so scores and labels are readable.
- Pause for 1–2 seconds after each `result:` line before speaking over it — let the viewer read it.
- For Demo 3, slow down at the FIX notice — that's the most important moment in the demo.
- You can run `evaluate.py` with `| head -60` if the output scrolls off screen, but the full output is better if your terminal window is tall enough.
