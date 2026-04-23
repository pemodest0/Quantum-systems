# Local Physics Assistant

This is the strict local assistant for the transport lab. It uses local retrieval first. Fine-tuning is intentionally out of scope for v1.

## Build the index

```powershell
python scripts\build_physics_curriculum_index.py --backend ollama_embeddings
```

If Ollama is unavailable, the script can fall back to lexical retrieval and records the reason in:

```text
outputs/transport_networks/local_rag/physics_assistant_index_manifest.json
```

## Ask a question

```powershell
python scripts\query_physics_assistant.py "Explique sink, loss e dephasing" --mode tutor --strict
```

The default generation profile is conservative for this machine:

- `--num-gpu 0`: forces CPU generation to avoid CUDA crashes on a 4 GB GTX 1650.
- `--num-ctx 1536`: avoids large context memory spikes.
- `--num-thread 4`: leaves CPU headroom for VS Code and light foreground use.
- `--keep-alive 0s`: unloads the generation model after each answer.

Profiles:

```powershell
python scripts\query_physics_assistant.py "Explique dephasing" --profile stable
python scripts\query_physics_assistant.py "Explique dephasing" --profile game
python scripts\query_physics_assistant.py "Explique dephasing" --no-generate
```

- `stable`: CPU generation with conservative memory limits.
- `game`: smaller context, shorter answer, two CPU threads, CPU-only.
- `--no-generate`: retrieval only. This is the safest option while playing.

Health check:

```powershell
python scripts\check_local_llm_health.py
```

Available modes:

- `tutor`: simple explanation in PT-BR.
- `critic`: checks overclaims, weak statistics, and confused observables.
- `paper_matcher`: compares a result with local paper cards.
- `lab_analyst`: explains campaign numbers and figures.
- `planner`: suggests one next campaign, without running it.

Useful retrieval-only mode:

```powershell
python scripts\query_physics_assistant.py "unfavorable ring target" --mode paper_matcher --strict --no-generate
```

## Evaluate the assistant base

```powershell
python scripts\evaluate_physics_assistant.py
```

The evaluation is retrieval-focused. Acceptance requires:

- at least 80 percent pass rate;
- zero hallucination-guard violations;
- no confusion between target arrival and spreading in controlled tests;
- no strong-effect language for gain below `0.02`.

## Strict policy

In strict mode, the assistant must not make strong physics claims without a local source, paper card, campaign result, or calculation. If support is missing, it should say that the current local base is insufficient.

## Current practical note

Embeddings use `nomic-embed-text`. Generation uses `qwen2.5:7b` when Ollama can run it. If the local runner fails because of memory/session instability, the query script still returns ranked sources so the answer remains auditable.
