import hashlib
import json
import time
import os
import ecdsa
import binascii
from flask import Flask, jsonify, request

# ==========================================
# 1. CRYPTOGRAPHIC ENGINE & WALLETS
# ==========================================
class Wallet:
    def __init__(self):
        self.private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        
    def get_address(self):
        return binascii.hexlify(self.public_key.to_string()).decode()

    def sign_transaction(self, transaction_data):
        data_str = json.dumps(transaction_data, sort_keys=True)
        return binascii.hexlify(self.private_key.sign(data_str.encode())).decode()

class Transaction:
    def __init__(self, sender_address, receiver_address, amount, signature=None):
        self.sender = sender_address
        self.receiver = receiver_address
        self.amount = amount
        self.signature = signature

    def to_dict(self):
        return {"sender": self.sender, "receiver": self.receiver, "amount": self.amount}

    def is_valid(self):
        if self.sender == "SYSTEM":
            return True
        if not self.signature:
            return False
        try:
            pub_key_bytes = binascii.unhexlify(self.sender)
            pub_key = ecdsa.VerifyingKey.from_string(pub_key_bytes, curve=ecdsa.SECP256k1)
            sig_bytes = binascii.unhexlify(self.signature)
            data_str = json.dumps(self.to_dict(), sort_keys=True)
            return pub_key.verify(sig_bytes, data_str.encode())
        except Exception:
            return False

class Block:
    def __init__(self, index, transactions, previous_hash=''):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        if self.index == 0:
            tx_data = self.transactions
        else:
            tx_data = [tx.to_dict() if isinstance(tx, Transaction) else tx for tx in self.transactions]
            
        data_string = json.dumps(tx_data, sort_keys=True)
        block_string = f"{self.index}{self.timestamp}{data_string}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    def __init__(self, difficulty=3):
        self.difficulty = difficulty
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.peers = set()

    def create_genesis_block(self):
        zypto_metadata = {
            "name": "Zypto",
            "symbol": "ZYP",
            "total_supply": 1000000000,
            "logo_design": "Round blue (#0000FF) icon with white Z",
            "owner": "Founder"
        }
        genesis = Block(0, zypto_metadata, "0")
        genesis.mine_block(self.difficulty)
        return genesis

    def get_latest_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        if transaction.is_valid():
            self.pending_transactions.append(transaction)
            return True
        return False

    def mine_pending_transactions(self, miner_address):
        reward_tx = Transaction("SYSTEM", miner_address, 50)
        self.pending_transactions.append(reward_tx)

        new_block = Block(len(self.chain), self.pending_transactions, self.get_latest_block().hash)
        new_block.mine_block(self.difficulty)
        
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

# ==========================================
# 2. LIVE NETWORK REST API (NODE ENDPOINTS)
# ==========================================
app = Flask(__name__)
zypto_chain = Blockchain(difficulty=3)

@app.route('/chain', methods=['GET'])
def get_full_chain():
    chain_data = []
    for block in zypto_chain.chain:
        txs = block.transactions if block.index == 0 else [tx.to_dict() if isinstance(tx, Transaction) else tx for tx in block.transactions]
        chain_data.append({
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": txs,
            "nonce": block.nonce,
            "hash": block.hash,
            "previous_hash": block.previous_hash
        })
    return jsonify({"length": len(chain_data), "chain": chain_data, "valid": zypto_chain.is_chain_valid()}), 200

@app.route('/mine', methods=['GET'])
def mine_block_endpoint():
    miner_address = request.args.get('address', 'Founder_Node_Wallet')
    mined_block = zypto_chain.mine_pending_transactions(miner_address)
    return jsonify({
        "message": f"Block #{mined_block.index} successfully mined!",
        "hash": mined_block.hash,
        "nonce": mined_block.nonce
    }), 200

@app.route('/wallet/new', methods=['GET'])
def generate_wallet():
    w = Wallet()
    return jsonify({
        "address": w.get_address(),
        "status": "Keep private key secure in local environment"
    }), 200

if __name__ == '__main__':
    print("Zypto Network Node Starting...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
