# Context-engineering experiments

Record each experiment so `docs/Reflections.md` can cite real results.

## Template
- **Question:** e.g. does a short CLAUDE.md plus on-demand spec reading beat pasting all specs upfront?
- **Setup:** task, agent, model, context given (files, size), what varied.
- **Measure:** tokens in/out, cache hits, retries, correctness of result, time.
- **Result:**
- **Conclusion / change made:**

## Planned experiments
1. Upfront vs on-demand context for the spec-writer.
2. Instruction placement in CLAUDE.md (top vs bottom) and whether rules are followed.
3. Model choice per task (sonnet vs opus) for cost versus quality.
4. Effect of extra context on an agent (signals of degradation).
5. Prompt/cache structure for the in-app AI features (stable prefix first).

## Results
