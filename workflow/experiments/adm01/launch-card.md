# ADM-01 launch card (per arm)

Worktrees (project root for the arm session), branch `exp/adm01-<arm>`, all cut from tag `adm01-start`:

| Arm | Folder | Prompt |
|---|---|---|
| A | `..\adm01-wt\A` | `prompts/arm-template.md` |
| H3 | `..\adm01-wt\H3` | `prompts/arm-template.md` |
| H1 | `..\adm01-wt\H1` | `prompts/arm-template.md` |
| H2 | `..\adm01-wt\H2` | `prompts/arm-template.md` |
| C | `..\adm01-wt\C` | `prompts/arm-C.md` |

Order: A, H3, H1, H2, C. Cap: A 15 USD; later arms 1.5 x A's cost, max 15 USD.

Before each arm (gate G3)
1. In a fresh terminal, `/usage`; give the coordinator the numbers. Start only with headroom >= cap (A: about 15 USD-equivalent).
2. Start >= 65 min after the previous arm's last request.
3. Docker + postgres:16 on 127.0.0.1:55432 must be up before grading (not needed for the arm run).

Run
1. Open VS Code on the arm folder (as the project root), start a NEW Claude Code session, same permission mode for every arm.
2. Paste the arm's prompt file contents. Do not add hints.
3. Note every time you intervene or wait > 60 s, and what you did.
4. When it reports done (or you stop it at the cap), close it, then start a coordinator session in the main folder and paste: *Resume Plan 2 from state.json*.
