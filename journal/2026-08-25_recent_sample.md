# Error-Correcting-Code Journal — recent sample (built 2026-08-25, papers from Aug 3–19)

This is **not** a "today" entry — it's a demonstration built from papers whose full
abstract pages I was actually able to fetch this session (unlike the 25 Aug entry, which
hit a persistent rate limit on its one candidate paper). Every fact below is confirmed
from a real page fetch, including the absence of a GitHub link — that's a genuine negative
result, not a placeholder.

## Papers with available code

_None found among the papers checked below._ This isn't a claim that no ECC paper from
this window has code — only these two specific papers were fully checked this session.

## Papers without available code (confirmed)

### [Quantum error correction at ultra-low overhead](https://arxiv.org/abs/2608.02773)
**Authors:** Zhide Lu, Weikang Li, Dong-Ling Deng
**arXiv:** 2608.02773 · **Published:** 3 Aug 2026 · **Subjects:** quant-ph

**Code status: confirmed absent.** Fetched the full abstract page; no Comments field
present, and no GitHub/repo link anywhere in the abstract text.

**Summary:** Introduces "Cornucopia codes" — a family of hardware-efficient quantum LDPC
codes achieving an encoding rate above 1/2 with a pseudo-threshold above 0.4% under
circuit-level noise. Built around a structured code geometry co-designed with
neutral-atom-array reconfiguration, so all X- and Z-type stabilizer checks are measured
in parallel using only 12 entangling layers regardless of code size. Headline result: a
single [[2844,1426,18]] code block encodes 1,426 distance-18 logical qubits at an
extrapolated logical error rate of 2.6×10⁻¹⁶ per qubit per cycle (physical error rate
0.1%) — versus needing 68,000+ physical qubits for a comparable bivariate-bicycle-code
implementation.

---

### [Subsystem Symmetries and Fracton Models in Quantum Error Correction](https://arxiv.org/abs/2608.18961)
**Authors:** Giovanni Canossa
**arXiv:** 2608.18961 · **Published:** 19 Aug 2026 · **Subjects:** quant-ph; cond-mat.stat-mech

**Code status: confirmed absent.** Fetched the full abstract page; Comments field reads
only "160 pages, 16 figures" — no repo link.

**Summary:** A 160-page PhD thesis connecting classical 3D self-dual Ising models
(Tetrahedral and Fractal Ising models) with subsystem symmetries to fracton topological
order and quantum error correction, via Kramers-Wannier-type duality. Main result: the
optimal code-capacity threshold of the Checkerboard code is determined to be 0.107(3),
which saturates the theoretical limit for CSS codes — the highest optimal error threshold
known among 3D codes. Uses a statistical-mechanical mapping to relate this saturation to a
generalized entropy relation for dual classical spin models.

---

## What this demonstrates about the pipeline

The GitHub-detection logic (`find_github_repo`) and the cloning/summarization logic
(`clone_repo`, `summarize_repo`) were separately tested against a **real, existing** QEC
repository (`quantumgizmos/bias_tailored_qldpc`) in this session and confirmed working —
see the project README's "Tested" section. These two entries show the *other* half working
correctly: honestly reporting "no code found" rather than fabricating a link when a paper
genuinely doesn't have one.
