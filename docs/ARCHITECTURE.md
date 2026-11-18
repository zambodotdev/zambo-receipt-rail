# Architecture

Three parts, deliberately small:

1. **The rail** (`src/rail.py`) — a local store of operation records keyed by
   an operation key that is created and persisted BEFORE the first payment
   attempt. A record holds the parameters, an optional pending transaction
   hash (written the moment a transfer is broadcast), and, once settled, the
   result and its receipt id.

2. **The flow** (`src/pay.py`) — decides by state, never by hope:
   - record + result -> REPLAY (return the stored result; send nothing)
   - no record -> PROCEED (a fresh, knowing first run)
   - record, no result -> UNKNOWN: read the pending transaction back from
     the chain. Settled: complete the record from the chain's own data.
     Not settled: only then is a (re)send safe.
   This is the lost-response problem stated as a state machine: a process can
   die after the payment and before the result is saved, and the resume path
   must not guess.

3. **The receipt** (`src/receipt.py`) — when a payment settles, the flow
   issues an AER-1 receipt committing to the exact stored output: the
   transaction hash, network, token, amount, parties, and block. The receipt
   carries the canonical bytes of its payload and the SHA-256 of those bytes
   (`output_hash`), so anyone can recompute the digest and check the saved
   result was not changed. Receipts prove the saved result was not changed;
   they do not claim the result was right.

Chain access (`src/chain.py`) is plain JSON-RPC against the Aevum testnet
with local EIP-1559 signing: no framework between the reader and the chain.
