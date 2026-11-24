# S1 — power of a shared-key test for Z13 + Z32 (synthetic pairs only)

Question: if one key enciphered both a 13-symbol and a 32-symbol message (sharing 3-7 symbols, like Z13 and Z32's
five), can a solver-based test detect it?

Test: Δ = best joint score with the shared symbols linked − best score with no links (zbot anneal, 5-gram LM,
homophonic key, 4 restarts); null = 99 fake link sets; p = rank. 40 shared-key pairs, 40 independent-key controls,
Z340-like homophone allocation, Z13-like (no cycling) and Z32-like (cycling) encipherment. Never used real Z13/Z32.

| | result |
|---|---|
| power at α = 0.05 (shared key detected) | **0.075** (95% CI 0.026-0.199) |
| power at α = 0.01 | 0.000 |
| false-positive rate at α = 0.05 | 0.050 (well calibrated) |
| seconds per solve / run-to-run noise | 1.86 s / 0.20 nats |

Verdict: **no power.** The solver's best readings of 13- and 32-letter ciphers are fluent but wrong, so they are no
more consistent with the true links than with fake ones. The ~19.6 bits a shared key would add exist on paper, but a
max-score test under a 5-gram model can't use them: that needs a plaintext prior strong enough to put the true
messages near the top (message entropy below the constraint), e.g. a much stronger language model.
Consequence (S2, as pre-declared): the real Z13+Z32 shared-key test is NOT run; it is "not testable with current tools".
The bench (bench.py + power.py) is kept: any stronger scorer must first show power here before touching the real ciphers.
