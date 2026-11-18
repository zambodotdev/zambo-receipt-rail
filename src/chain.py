"""Minimal Aevum (QDay testnet) chain access: JSON-RPC + local signing.

No web3 dependency: plain requests for RPC and eth_account for signing,
which keeps the demo reproducible anywhere.
"""
import requests
from eth_account import Account

RPC_URL = "https://rpc-test.qday.info"
CHAIN_ID = 44005
EXPLORER = "https://explorer-test.qday.info"
TUSD8 = "0x456569838f1d43009A91ebA4263147Afd7233483"
TUSD8_DECIMALS = 6

TRANSFER_SELECTOR = "a9059cbb"  # transfer(address,uint256)
BALANCE_SELECTOR = "70a08231"   # balanceOf(address)


class Chain:
    def __init__(self, rpc_url: str = RPC_URL):
        self.rpc = rpc_url
        self._id = 0

    def call(self, method, params):
        self._id += 1
        r = requests.post(
            self.rpc,
            json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params},
            timeout=30,
        )
        j = r.json()
        if "error" in j:
            raise RuntimeError(f"RPC {method}: {j['error']}")
        return j["result"]

    def tusd8_balance(self, address: str) -> int:
        data = "0x" + BALANCE_SELECTOR + address[2:].lower().rjust(64, "0")
        return int(self.call("eth_call", [{"to": TUSD8, "data": data}, "latest"]), 16)

    def native_balance(self, address: str) -> int:
        return int(self.call("eth_getBalance", [address, "latest"]), 16)

    def tx_receipt(self, tx_hash: str):
        return self.call("eth_getTransactionReceipt", [tx_hash])

    def send_tusd8(self, key: str, to: str, amount_units: int) -> str:
        acct = Account.from_key(key)
        nonce = int(self.call("eth_getTransactionCount", [acct.address, "pending"]), 16)
        base_fee = int(self.call("eth_gasPrice", []), 16)
        data = (
            "0x" + TRANSFER_SELECTOR
            + to[2:].lower().rjust(64, "0")
            + hex(amount_units)[2:].rjust(64, "0")
        )
        tx = {
            "chainId": CHAIN_ID,
            "nonce": nonce,
            "to": TUSD8,
            "value": 0,
            "data": data,
            "gas": 120000,
            "maxFeePerGas": base_fee * 2 + 10**9,
            "maxPriorityFeePerGas": 10**9,
        }
        signed = acct.sign_transaction(tx)
        return self.call("eth_sendRawTransaction", [signed.raw_transaction.hex()])

    def wait_receipt(self, tx_hash: str, tries: int = 40):
        import time

        for _ in range(tries):
            rcpt = self.tx_receipt(tx_hash)
            if rcpt is not None:
                return rcpt
            time.sleep(1.5)
        return None
