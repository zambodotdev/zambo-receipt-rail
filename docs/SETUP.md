# Setup

## Network (QDay Aevum testnet, from the official QDay links page)

| Field | Value |
|---|---|
| Chain ID | 44005 (0xABE5) |
| RPC | https://rpc-test.qday.info |
| Explorer | https://explorer-test.qday.info |
| Native token | tQDAY (18 decimals, gas) |
| tUSD8 | 0x456569838f1d43009A91ebA4263147Afd7233483 (6 decimals) |
| Faucet | https://faucet.qday.info (5 tQDAY per claim, 24h cooldown) |

## Run

```bash
pip install -r requirements.txt
# keys/agent.json: {"address": "0x...", "private_key": "0x..."}  (testnet only, never commit)
python -m src.pay --op job-001 --to <service-address> --amount 2.50 \
    --service "endpoint.ownership-verification" --key-file keys/agent.json
# simulate the crash the rail is built for, then resume:
python -m src.pay --op job-001 --to <service-address> --amount 2.50 \
    --service "endpoint.ownership-verification" --key-file keys/agent.json --crash-after-send
python -m src.pay --op job-001 --resume --key-file keys/agent.json
# run it again: REPLAY, nothing re-sends.
python -m src.pay --op job-001 --to <service-address> --amount 2.50 \
    --service "endpoint.ownership-verification" --key-file keys/agent.json
```

Verify any issued receipt with the published checker:

```bash
pip install aer1-verify
python -m aer1_verify receipts/<receipt-id>.json
```
