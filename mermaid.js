const recommendationFlow = `
flowchart TD
  subgraph INPUT["📥 INPUT — User Preferences"]
    A1[favorite_genre]
    A2[favorite_mood]
    A3[target_energy]
    A4[likes_acoustic]
  end

  subgraph PROCESS["⚙️ PROCESS — Score Every Song in the CSV"]
    B[Load songs.csv]
    B --> C{For each song...}

    C --> D1{Genre match?}
    D1 -- Yes --> S1[+genre points]
    D1 -- No  --> S1x[+0]

    C --> D2{Mood match?}
    D2 -- Yes --> S2[+mood points]
    D2 -- No  --> S2x[+0]

    C --> D3[Energy distance from target_energy]
    D3 --> S3[± energy adjustment]

    C --> D4{likes_acoustic?}
    D4 -- Yes --> S4[+ acoustic bonus]
    D4 -- No  --> S4x[+0]

    S1 & S1x & S2 & S2x & S3 & S4 & S4x --> TOTAL[Song Score]
    TOTAL --> COLLECT[Collect all scored songs]
  end

  subgraph OUTPUT["🏆 OUTPUT — Top K Recommendations"]
    SORT[Sort by score descending]
    TOPK[Return Top K songs]
    SORT --> TOPK
  end

  INPUT --> B
  COLLECT --> SORT
`;

export default recommendationFlow;

export const systemDiagram = `
flowchart TD
  USER([👤 Human User])
  DEV([🧑‍💻 Developer / Tester])

  subgraph DATA["💾 Data Layer"]
    CSV[(songs.csv\n18 songs · 10 features)]
  end

  subgraph RETRIEVER["📦 Retriever — recommender.py"]
    R1[load_songs\nparse CSV into dicts]
    R2[score_song\ngenre · mood · energy · acoustic]
    R3[recommend_songs\nsort → top K]
    R1 --> R2 --> R3
  end

  subgraph AGENT["🤖 Agent — agent.py · Claude API"]
    AG1[Parse natural language request]
    AG2[browse_catalog tool]
    AG3[get_recommendations tool]
    AG4[evaluate_quality tool]
    AG5{Quality OK?}
    AG6[Adjust params · retry]
    AG1 --> AG2 --> AG3 --> AG4 --> AG5
    AG5 -- No --> AG6 --> AG3
  end

  subgraph OUTPUT["🏆 Output"]
    OUT1[Ranked songs + scores + reasons]
    OUT2[Claude natural language explanation]
  end

  subgraph TESTING["🧪 Human-in-the-Loop Testing — tests/test_recommender.py"]
    T1[test_recommend_returns_songs_sorted_by_score]
    T2[test_explain_recommendation_returns_non_empty_string]
    T3{pytest pass?}
    T1 & T2 --> T3
    T3 -- Fail --> DEV
  end

  subgraph RUNNER["▶️ Runner — main.py"]
    M1[3 hardcoded profiles\nHigh-Energy Pop · Chill Lofi · Deep Rock]
    M2[Print scores & reasons]
    M1 --> M2
  end

  USER -- natural language --> AGENT
  USER -- structured prefs --> RUNNER
  CSV --> R1
  RETRIEVER --> AG3
  RETRIEVER --> RUNNER
  AG5 -- Yes --> OUTPUT
  OUTPUT --> USER
  RUNNER --> OUTPUT
  DEV -- run pytest --> TESTING
  TESTING -- T3 Pass --> DEV
`;

export const agentFlow = `
flowchart TD
  USER([🎵 User Natural Language Request])

  subgraph LOOP["🔄 Agentic Loop — up to 10 iterations"]

    IT["Print ── Iteration N ──"]

    subgraph OBSERVE["👁 Observable Intermediate Steps"]
      OB1["💭 Print Claude reasoning text\n(planning & self-correction narration)"]
      OB2["▶ Print step label  PLAN / ACT / CHECK"]
      OB3["Print tool input + result summary"]
      OB1 --> OB2 --> OB3
    end

    subgraph PLAN["🧠 PLAN — Claude Infers Preferences"]
      P1{Catalog needed?}
      P2["▶ PLAN — browse_catalog tool"]
      P3[Infer: genre · mood · energy · acoustic]
      P1 -- Yes --> P2 --> P3
      P1 -- No  --> P3
    end

    subgraph ACT["⚙️ ACT — Run Recommendation Engine"]
      A1["▶ ACT — get_recommendations tool"]
      A2[score_song × 18 songs · sort · top K]
      A1 --> A2
    end

    subgraph CHECK["🔍 CHECK — Self-Evaluate Quality"]
      C1["▶ CHECK — evaluate_quality tool"]
      C2{Quality?}
      C1 --> C2
    end

    subgraph FIX["🔧 FIX — Adjust & Retry"]
      F1["Print FIX notice to console"]
      F2[Adjust genre · mood · energy]
      F3{Retries < 2?}
      F1 --> F2 --> F3
    end

    IT --> OBSERVE --> PLAN --> ACT --> CHECK
    C2 -- good --> STOP([stop_reason = end_turn])
    C2 -- acceptable / poor --> FIX
    F3 -- Yes --> IT
    F3 -- No  --> STOP

  end

  subgraph OUTPUT["🏆 OUTPUT — Final Answer"]
    O1[Claude writes explanation]
    O2([Recommended songs + reasons])
    O1 --> O2
  end

  USER --> LOOP
  STOP --> OUTPUT
`;

