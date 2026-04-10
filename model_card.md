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

My biggest learning moment was seeing how much the exact scoring rules shape the output. A small weight change or a simple exact-match rule can make a lot of difference in what the model recommends. Using AI tools helped me explore ideas fast, but I still had to double-check the actual scoring and the dataset because the tools can suggest plausible logic that does not match the code. I was surprised that this simple algorithm could still feel like recommendation behavior when it pushed songs toward the requested genre, mood, and energy. Next I would try adding smoother energy and acoustic scoring, plus more diverse song features so the recommender feels less rigid.
