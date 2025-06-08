import asyncio
import os
import requests
import time
import threading
from web3 import Web3
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY'
BSCSCAN_API_KEY = 'YOUR_BSCSCAN_API_KEY'
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
COINMARKETCAP_API_KEY = 'YOUR_COINMARKETCAP_API_KEY'

ETH_RPC_URL = 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'
BSC_RPC_URL = 'https://bsc-dataseed.binance.org/'

WATCHED_WALLETS_FILE = "watched_wallets.txt"
LAST_BLOCK_FILE = "last_block.txt"

user_chat_ids = {}
watched_wallets = set()
MINIMUM_TRANSACTION_VALUE = 0.01

def load_watched_wallets():
    global watched_wallets
    if os.path.exists(WATCHED_WALLETS_FILE):
        with open(WATCHED_WALLETS_FILE, 'r') as f:
            watched_wallets = set(f.read().splitlines())

def save_watched_wallets():
    with open(WATCHED_WALLETS_FILE, 'w') as f:
        for wallet in watched_wallets:
            f.write(f"{wallet}\n")

def get_last_checked_block():
    if os.path.exists(LAST_BLOCK_FILE):
        with open(LAST_BLOCK_FILE, 'r') as f:
            return int(f.read())
    return 1

def save_last_checked_block(block_number):
    with open(LAST_BLOCK_FILE, 'w') as f:
        f.write(str(block_number))

def get_eth_wallet_transactions(wallet_address, from_block, to_block):
    web3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
    if web3.is_connected():
        try:
            transactions = []
            for block_number in range(from_block, to_block + 1):
                block = web3.eth.get_block(block_number, full_transactions=True)
                for tx in block['transactions']:
                    if tx['from'].lower() == wallet_address.lower() or tx['to'].lower() == wallet_address.lower():
                        transactions.append(tx)
            return transactions
        except Exception as e:
            print(f"Error fetching ETH transactions: {e}")
            return []
    else:
        print("Failed to connect to Ethereum.")
        return []

def get_bnb_wallet_transactions(wallet_address):
    try:
        url = f'https://api.bscscan.com/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={BSCSCAN_API_KEY}'
        response = requests.get(url)
        data = response.json()
        return data.get('result', [])
    except Exception as e:
        print(f"Error fetching BNB transactions: {e}")
        return []

def get_wallet_transactions(wallet_address, blockchain, from_block=None, to_block=None):
    try:
        if blockchain == 'eth':
            return get_eth_wallet_transactions(wallet_address, from_block, to_block)
        elif blockchain == 'bnb':
            return get_bnb_wallet_transactions(wallet_address)
        else:
            raise ValueError('Invalid blockchain specified')
    except Exception as e:
        print(f"Error fetching wallet transactions: {e}")
        return []

async def send_telegram_notification(bot, message, value, usd_value, tx_hash, blockchain, chat_id):
    try:
        explorer_link = f'<a href="https://etherscan.io/tx/{tx_hash}">Etherscan</a>' if blockchain == 'eth' else f'<a href="https://bscscan.com/tx/{tx_hash}">BscScan</a>'
        text = f'📢 {message}: {explorer_link}\n💰 Value: {value:.6f} {blockchain.upper()} (${usd_value:.2f})'
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telegram notification sent: {message}, value: {value} {blockchain.upper()} (${usd_value:.2f}) to chat_id {chat_id}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

async def start_command(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_chat_ids[user_id] = chat_id
    text = """
👋 Welcome to the Ethereum & Binance Wallet Monitoring Bot! 🚀

Use /add <blockchain> <wallet_address> to add a wallet to monitor. 🕵️
Example: /add ETH <wallet_address> or /add BNB <wallet_address>

Use /remove <blockchain> <wallet_address> to stop monitoring. 🗑️
Example: /remove ETH <wallet_address> or /remove BNB <wallet_address>

Use /list to list all monitored wallets. 📋
    """
    await message.answer(text)

async def add_wallet_command(message: Message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Please provide a blockchain and wallet address.\nUsage: /add ETH/BNB <wallet_address>")
        return
    blockchain = args[1].lower()
    wallet_address = args[2]
    if blockchain not in ['eth', 'bnb']:
        await message.answer("❌ Unsupported blockchain. Use: ETH or BNB")
        return
    watched_wallets.add(f"{blockchain}:{wallet_address}")
    save_watched_wallets()
    await message.answer(f"✅ Added {wallet_address} on {blockchain.upper()} to monitored wallets. 🕵️")

async def remove_wallet_command(message: Message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Please provide a blockchain and wallet address.\nUsage: /remove ETH/BNB <wallet_address>")
        return
    blockchain = args[1].lower()
    wallet_address = args[2]
    wallet_to_remove = f"{blockchain}:{wallet_address}"
    if wallet_to_remove in watched_wallets:
        watched_wallets.remove(wallet_to_remove)
        save_watched_wallets()
        await message.answer(f"🗑️ Removed {wallet_address} on {blockchain.upper()} from monitored wallets.")
    else:
        await message.answer(f"⚠️ {wallet_address} on {blockchain.upper()} is not being monitored.")

async def list_wallets_command(message: Message):
    chat_id = message.chat.id
    if watched_wallets:
        text = "📋 Currently monitored wallets:\n" + "\n".join(f"- {wallet}" for wallet in watched_wallets)
    else:
        text = "⚠️ No wallets are being monitored."
    await message.answer(text)

def monitor_wallets(bot):
    last_checked_block = get_last_checked_block()
    web3_eth = Web3(Web3.HTTPProvider(ETH_RPC_URL))
    while True:
        if web3_eth.is_connected():
            latest_block = web3_eth.eth.block_number
            if latest_block > last_checked_block:
                for wallet in watched_wallets:
                    blockchain, wallet_address = wallet.split(':')
                    if blockchain == 'eth':
                        transactions = get_wallet_transactions(wallet_address, blockchain, last_checked_block + 1, latest_block)
                        for tx in transactions:
                            if tx['from'].lower() == wallet_address.lower() or tx['to'].lower() == wallet_address.lower():
                                value = float(tx['value']) / 10**18
                                if value >= MINIMUM_TRANSACTION_VALUE:
                                    tx_hash = tx['hash']
                                    usd_value = get_usd_value(value, blockchain)
                                    for chat_id in user_chat_ids.values():
                                        asyncio.run_coroutine_threadsafe(
                                            send_telegram_notification(bot, "New transaction detected", value, usd_value, tx_hash, blockchain, chat_id),
                                            bot.loop
                                        )
                    elif blockchain == 'bnb':
                        transactions = get_wallet_transactions(wallet_address, blockchain)
                        for tx in transactions:
                            if 'hash' in tx and 'value' in tx:
                                value = float(tx['value']) / 10**18
                                if value >= MINIMUM_TRANSACTION_VALUE:
                                    tx_hash = tx['hash']
                                    usd_value = get_usd_value(value, blockchain)
                                    for chat_id in user_chat_ids.values():
                                        asyncio.run_coroutine_threadsafe(
                                            send_telegram_notification(bot, "New transaction detected", value, usd_value, tx_hash, blockchain, chat_id),
                                            bot.loop
                                        )
                save_last_checked_block(latest_block)
        time.sleep(60)

def get_usd_value(value, blockchain):
    try:
        url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={"ETH" if blockchain == "eth" else "BNB"}'
        headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
        response = requests.get(url, headers=headers)
        data = response.json()
        price = data['data']['ETH' if blockchain == 'eth' else 'BNB']['quote']['USD']['price']
        return value * price
    except Exception as e:
        print(f"Error fetching USD price: {e}")
        return value * 3000 if blockchain == 'eth' else value * 500

def start_monitoring(bot):
    monitor_thread = threading.Thread(target=monitor_wallets, args=(bot,))
    monitor_thread.daemon = True
    monitor_thread.start()

async def main():
    load_watched_wallets()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(start_command, Command(commands=["start"]))
    dp.message.register(add_wallet_command, Command(commands=["add"]))
    dp.message.register(remove_wallet_command, Command(commands=["remove"]))
    dp.message.register(list_wallets_command, Command(commands=["list"]))
    start_monitoring(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
