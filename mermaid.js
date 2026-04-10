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
