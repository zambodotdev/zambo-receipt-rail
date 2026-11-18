# Zambo Receipt Rail

An agent payment flow on the Aevum testnet (QDay) where every tUSD8 payment
settles with a verifiable AER-1 execution receipt: the payment and the work it
paid for can both be checked by anyone, from the committed bytes alone.

Entry for the Aevum Builder Challenge #1 (DoraHacks).

## The problem

An agent that pays for a service has two failure modes nobody can audit after
the fact: it pays twice when a process dies after the payment but before the
result is recorded, or it cannot prove what it paid for. This rail closes both:

- Every payment is issued under an operation key created and stored BEFORE the
  first attempt. Retries and resumes look the key up first.
- The lookup has three states. Record + result: return the stored result,
  never pay again. No record: proceed, knowingly. Record, no result: UNKNOWN —
  reconcile against the chain by the key before any re-send; both naive
  defaults (pay again, or assume it never ran) are wrong.
- When a payment settles, the rail writes an AER-1 receipt committing to the
  exact stored output (transaction, amounts, parties, the work record). Anyone
  can recompute the receipt's output_hash from its canonical bytes and check
  the saved result was not changed.

## Layout

- `src/rail.py` — the payment rail: operation-key store, three-state lookup,
  tUSD8 transfer on Aevum, receipt issuance.
- `src/receipt.py` — AER-1 receipt construction + local verification
  (aer1-verify compatible).
- `docs/` — architecture, reproduction steps, testnet addresses.

## Status

Scaffold. Chain parameters land from the official starter kit; see docs/SETUP.md.
