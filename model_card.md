# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

This recommender suggests songs based on a user’s genre, mood, energy, and acoustic preference. It is meant for simple playlist-style recommendations and classroom exploration. It should not be used as a full music discovery engine for real production users.

---

## 3. How the Model Works

The model gives each song a score by checking a few preferences. It adds points when the song matches the requested genre or mood. It also rewards songs whose energy level is close to the target energy. If the user likes acoustic music, it adds a small bonus for very acoustic songs. The highest scoring songs are recommended first.

---

## 4. Data

The dataset has 18 songs with labels for genre, mood, energy, tempo, valence, danceability, and acousticness. It includes pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, folk, reggae, blues, metal, country, and world music. It is small and missing many styles, so the recommender can only work within this limited catalog.

---

## 5. Strengths

The system works well for clear preferences like high-energy pop or chill lofi. It captures mood and genre matches cleanly when the labels align. It also moves results in the right direction when energy is part of the profile.

---

## 6. Limitations and Bias

The system favors exact genre and mood labels, so similar styles can be ignored if they use different words. Energy is only rewarded in a narrow range, so extreme low or high energy users may not see good matches. Acoustic preference is treated as a small bonus, so it can be overshadowed by genre or mood.

---

## 7. Evaluation

I tested three profiles: High-Energy Pop, Chill Lofi, and Deep Intense Rock. I looked for whether the top songs matched the requested genre, mood, and energy level. The model gave upbeat happy songs to the pop profile and calm low-energy songs to the lofi profile. It also showed intense rock music for the rock profile. The surprising finding was that the acoustic preference had less influence than genre and mood.

---

## 8. Ideas for Improvement

- Use normalized genre and mood matching so similar labels work together.
- Make energy scoring smoother instead of giving zero credit for some songs.
- Add more musical features like tempo, valence, and danceability to improve variety.

---

## 9. Intended Use and Non-Intended Use

This system is intended for simple music recommendation experiments and small playlists. It is not intended for replacing real music services, handling complex user tastes, or making production-level personalization decisions.

---

## 10. Personal Reflection

Building this project changed how I think about AI systems. The rule-based recommender made the scoring logic completely transparent — I could trace exactly why any song was recommended. Adding the Claude agent on top showed me that even a "smart" AI is most useful when it's connected to reliable, deterministic tools rather than trying to do everything itself. The agent is better at fuzzy reasoning (interpreting a vague mood request, judging whether results feel right) while `score_song()` is better at precise arithmetic. That division of labor — language model for judgment, deterministic code for computation — feels like the right pattern for most real applications.

The retry loop also taught me something about AI reliability: a single model call can be wrong, but a model that checks its own output and corrects it is meaningfully more robust. The quality evaluation step isn't perfect, but it adds a layer of accountability that a one-shot call doesn't have. In a real product, that kind of self-verification loop — even a simple one — could catch a lot of bad recommendations before they reach a user.

---

### Limitations and Biases

The scoring formula weights genre (+5) and mood (+4) far above everything else, which means a song with a perfect energy and acoustic fit but a different genre will always lose to a weaker genre match. This creates a genre bubble: once a user picks "pop," the system rarely surfaces anything outside pop, even when another genre might serve the request better. The catalog itself introduces a second bias — with only 18 songs, niche genres like blues, reggae, and country are effectively invisible to the agent no matter how parameters are tuned. There is also no concept of listening history or fatigue, so the same top-scored songs appear for every request that shares a genre and mood.

---

### Could This AI Be Misused?

The recommender itself is low-risk, but two misuse patterns are worth noting. First, the system prompt tells Claude exactly which genres and moods exist in the catalog — a malicious user could craft a request that floods the agent with retries by asking for combinations that will never score well, wasting API credits. This is mitigated by the hard cap of 2 retries and the 10-iteration loop limit. Second, if the catalog CSV were replaced with user-submitted data, someone could inject song entries with inflated scores or offensive metadata and have Claude surface them in recommendations. Preventing this requires validating CSV data on load (type checks, value range checks) and never treating catalog fields as trusted HTML or executable content.

---

### What Surprised Me About Testing

The most surprising result was how fragile the `Recommender` OOP class was before testing caught it. The `recommend()` method was silently returning songs in insertion order rather than by score, and the two starter tests still passed — because the pop song happened to be added first in the fixture. Without tests that checked a different user profile (lofi instead of pop), that bug would have gone unnoticed. It was a good reminder that a passing test suite is only as trustworthy as the assumptions baked into the fixtures. The second surprise came from the evaluation harness: SC-11 (unknown genre) returned a confidence of only 0.46, while every known-genre profile scored 0.90 or above. The gap is much larger than expected — it shows that genre match alone contributes nearly half the maximum score, so any request the agent can't map to a catalog genre produces noticeably weaker results even when the rest of the parameters fit well.

---

### Collaboration with AI

Claude was involved throughout this project as both a coding assistant and the intelligence running the agent loop itself.

**Helpful suggestion:** When adding the agentic workflow, Claude suggested separating the scoring engine (`score_song` in `recommender.py`) from the agent's tool dispatcher (`_execute_tool` in `agent.py`) rather than reimplementing scoring logic inside the agent. This turned out to be the right call — the scoring function became independently testable with `pytest`, the agent stayed lightweight, and fixing a scoring bug in one place automatically fixed it everywhere.

**Flawed suggestion:** Claude initially described the `Recommender.recommend()` OOP method as functioning correctly in comments and documentation, when in reality it was still a placeholder returning `self.songs[:k]` (insertion order, not sorted by score). The documentation said the system was "working" before the tests actually verified it. This was a good illustration of why AI-generated descriptions of code should always be checked against the code itself — the AI described intended behavior, not actual behavior.
