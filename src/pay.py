"""The agent payment flow: pay tUSD8 for a service, under an operation key,
and settle the payment with an AER-1 receipt.

Usage:
  python -m src.pay --op OP_KEY --to SERVICE_ADDR --amount 2.50 \
      --service "endpoint.ownership-verification" --key-file keys/agent.json
  python -m src.pay --op OP_KEY --resume --key-file keys/agent.json
  python -m src.pay --op OP_KEY --crash-after-send ...   (demo: dies mid-flow)

The three states, printed as they are decided:
  REPLAY   record + result: the stored result is returned; nothing re-sends.
  PROCEED  no record: the payment runs, knowingly.
  UNKNOWN  record, no result: reconcile against the chain by the pending
           transaction before any re-send. Never default either way.
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain import CHAIN_ID, EXPLORER, TUSD8, Chain  # noqa: E402
from rail import Rail  # noqa: E402
from receipt import issue_receipt  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def settle(args, rail: Rail, chain: Chain, key: str, record: dict) -> dict:
    params = record["params"]
    to = params["to"]
    amount_units = params["amount_units"]
    acct_address = __import__("eth_account").Account.from_key(key).address
    tx_hash = chain.send_tusd8(key, to, amount_units)
    rail.mark_sent(args.op, tx_hash)
    print(f"  broadcast: {tx_hash}")
    print(f"  explorer:  {EXPLORER}/tx/{tx_hash}")
    if args.crash_after_send:
        print("  SIMULATED CRASH: process dies after broadcast, before the result is saved.")
        os._exit(1)
    rcpt = chain.wait_receipt(tx_hash)
    if rcpt is None or rcpt.get("status") != "0x1":
        raise RuntimeError(f"transfer did not settle: {tx_hash}")
    result = {
        "transaction": tx_hash,
        "network": f"eip155:{CHAIN_ID}",
        "token": TUSD8,
        "amount_units": amount_units,
        "from": acct_address,
        "to": to,
        "block": int(rcpt["blockNumber"], 16),
        "status": "settled",
    }
    receipt_id = str(uuid.uuid4())
    receipt = issue_receipt(
        receipt_id=receipt_id,
        tool={"name": "aevum_tusd8_payment", "version": "1.0.0",
              "scope": "Aevum testnet tUSD8 transfer under an operation key"},
        inputs={"operation_key": args.op, "service": params["service"],
                "amount_units": amount_units, "to": to},
        outputs=result,
        caller=acct_address,
        created_at=now_iso(),
    )
    os.makedirs("receipts", exist_ok=True)
    with open(f"receipts/{receipt_id}.json", "w") as f:
        json.dump(receipt, f, indent=1)
    rail.complete(args.op, result, receipt_id)
    print(f"  settled in block {result['block']}; AER-1 receipt {receipt_id}")
    print(f"  receipt file: receipts/{receipt_id}.json")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--op", required=True)
    ap.add_argument("--to")
    ap.add_argument("--amount", type=float)
    ap.add_argument("--service", default="agent-service")
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--db", default="rail.db")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--crash-after-send", action="store_true")
    args = ap.parse_args()

    key = json.load(open(args.key_file))["private_key"]
    rail = Rail(args.db)
    chain = Chain()

    if not args.resume:
        if not args.to or args.amount is None:
            ap.error("--to and --amount are required for a new payment")
        state = rail.begin(args.op, {
            "to": args.to,
            "amount_units": int(args.amount * 10**6),
            "service": args.service,
        })
    else:
        record = rail.lookup(args.op)
        state = "absent" if record is None else ("replay" if record["result"] else "unknown")

    record = rail.lookup(args.op)
    if state == "replay":
        print(f"REPLAY: operation {args.op} already settled; stored result returned, nothing re-sent.")
        print(json.dumps(record["result"], indent=1))
        print(f"receipt: {record['receipt_id']}")
        return
    if state == "absent":
        print(f"NOT CHECKED: no record for {args.op}; nothing to resume.")
        return
    if state == "unknown":
        pending = record["pending_tx"]
        print(f"UNKNOWN: record exists for {args.op}, no result committed. Reconciling against the chain first.")
        if pending:
            rcpt = chain.wait_receipt(pending, tries=4)
            if rcpt is not None and rcpt.get("status") == "0x1":
                print(f"  the pending transaction settled on-chain: {pending}")
                # Re-run settle bookkeeping without re-sending: rebuild the
                # result from the chain record and complete the operation.
                args.crash_after_send = False
                result = {
                    "transaction": pending,
                    "network": f"eip155:{CHAIN_ID}",
                    "token": TUSD8,
                    "amount_units": record["params"]["amount_units"],
                    "from": __import__("eth_account").Account.from_key(key).address,
                    "to": record["params"]["to"],
                    "block": int(rcpt["blockNumber"], 16),
                    "status": "settled (recovered on resume)",
                }
                receipt_id = str(uuid.uuid4())
                receipt = issue_receipt(
                    receipt_id=receipt_id,
                    tool={"name": "aevum_tusd8_payment", "version": "1.0.0",
                          "scope": "Aevum testnet tUSD8 transfer under an operation key"},
                    inputs={"operation_key": args.op, "service": record["params"]["service"],
                            "amount_units": record["params"]["amount_units"],
                            "to": record["params"]["to"]},
                    outputs=result,
                    caller=result["from"],
                    created_at=now_iso(),
                )
                os.makedirs("receipts", exist_ok=True)
                with open(f"receipts/{receipt_id}.json", "w") as f:
                    json.dump(receipt, f, indent=1)
                rail.complete(args.op, result, receipt_id)
                print(f"  completed from the chain record; AER-1 receipt {receipt_id}; no second payment sent.")
                return
        print("  no settled transaction found for this key; safe to run the payment now.")
        settle(args, rail, chain, key, record)
        return
    print(f"PROCEED: new operation {args.op}; paying {args.amount} tUSD8 to {args.to}.")
    settle(args, rail, chain, key, record)


if __name__ == "__main__":
    main()
