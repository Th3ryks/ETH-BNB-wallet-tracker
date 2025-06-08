# 💸 Wallet Watcher Bot 📲

Monitor Ethereum and Binance Smart Chain wallets with real-time Telegram alerts!
This bot tracks blockchain wallet activity and notifies you about new transactions directly in Telegram. 👷‍♂️🚀

---

## 🔧 Features

* 📬 Real-time alerts for ETH and BNB transactions
* 📈 USD value calculation using CoinMarketCap
* 🛁 Monitoring via Infura RPC and BscScan API
* ✅ Manage watched wallets directly from Telegram
* 💾 Persistent wallet and block tracking across restarts

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/wallet-watcher-bot.git
cd wallet-watcher-bot
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Set your API keys and RPC URLs in the script or with environment variables:

```python
ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY'
BSCSCAN_API_KEY = 'YOUR_BSCSCAN_API_KEY'
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
COINMARKETCAP_API_KEY = 'YOUR_COINMARKETCAP_API_KEY'
ETH_RPC_URL = 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'
BSC_RPC_URL = 'https://bsc-dataseed.binance.org/'
```

---

## ▶️ Running the Bot

```bash
python your_script.py
```

---

## 💬 Telegram Bot Commands

| Command                       | Description                         |
| ----------------------------- | ----------------------------------- |
| `/start`                      | 👋 Welcome message and instructions |
| `/add <ETH/BNB> <address>`    | ➕ Add a wallet to monitor           |
| `/remove <ETH/BNB> <address>` | ❌ Remove a monitored wallet         |
| `/list`                       | 📋 Show list of watched wallets     |

Examples:

```
/add ETH 0x123abc...
/remove BNB 0x456def...
```

---

## 🧠 How It Works

* Checks for new Ethereum blocks or uses BscScan for BNB
* Scans for relevant transactions (from/to watched wallets)
* If value ≥ `0.01` ETH/BNB, sends a Telegram alert
* USD value calculated via CoinMarketCap API 💰

---

## 📂 Files

* `watched_wallets.txt` — list of wallets being monitored
* `last_block.txt` — last checked Ethereum block

---

## 🛠️ Dependencies

* `web3`
* `requests`
* `aiogram`
* `asyncio`

Install dependencies with:

```bash
pip install web3 requests aiogram
```

---

## ☁️ Sample Notification

```
📢 New transaction detected: Etherscan
💰 Value: 1.234567 ETH ($2,345.67)
```
