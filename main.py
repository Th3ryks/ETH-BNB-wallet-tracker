import requests
import json
import time
import os
from web3 import Web3
import threading
from telegram.ext import CommandHandler, Updater

# Your API keys and tokens
ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY'  # Replace with your Etherscan API key
BSCSCAN_API_KEY = 'YOUR_BSCSCAN_API_KEY'     # Replace with your BscScan API key
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Replace with your Telegram bot token
COINMARKETCAP_API_KEY = 'YOUR_COINMARKETCAP_API_KEY'  # Replace with your CoinMarketCap API key

# RPC URL for MoChain
MOCHAIN_RPC_URL = 'https://mainnet.mochain.app/api/eth-rpc'

# File to store watched wallets
WATCHED_WALLETS_FILE = "watched_wallets.txt"
LAST_BLOCK_FILE = "last_block.txt"

# Dictionary to store users' chat IDs and monitored wallets
user_chat_ids = {}
watched_wallets = set()

# Function to load watched wallets from a file
def load_watched_wallets():
    global watched_wallets
    if os.path.exists(WATCHED_WALLETS_FILE):
        with open(WATCHED_WALLETS_FILE, 'r') as f:
            wallets = f.read().splitlines()
            watched_wallets = set(wallets)

# Function to save watched wallets to a file
def save_watched_wallets():
    with open(WATCHED_WALLETS_FILE, 'w') as f:
        for wallet in watched_wallets:
            f.write(f"{wallet}\n")

# Function to retrieve the last processed block
def get_last_checked_block():
    if os.path.exists(LAST_BLOCK_FILE):
        with open(LAST_BLOCK_FILE, 'r') as f:
            return int(f.read())
    return 1  # If no file exists, start from block 1

# Function to save the last processed block
def save_last_checked_block(block_number):
    with open(LAST_BLOCK_FILE, 'w') as f:
        f.write(str(block_number))

# Function to get all transactions of a MoChain wallet
def get_mo_wallet_transactions(wallet_address, from_block, to_block):
    web3 = Web3(Web3.HTTPProvider(MOCHAIN_RPC_URL))
    if web3.is_connected():  # Updated isConnected() -> is_connected()
        try:
            transactions = []

            # Loop through each block from from_block to to_block
            for block_number in range(from_block, to_block + 1):
                block = web3.eth.get_block(block_number, full_transactions=True)
                for tx in block['transactions']:
                    # If the transaction belongs to the specified wallet
                    if tx['from'].lower() == wallet_address.lower() or tx['to'].lower() == wallet_address.lower():
                        transactions.append(tx)

            return transactions
        except Exception as e:
            print(f"Error fetching MoChain transactions: {e}")
            return []
    else:
        print("Failed to connect to MoChain.")
        return []

# Function to retrieve wallet transactions based on the blockchain
def get_wallet_transactions(wallet_address, blockchain, from_block, to_block):
    try:
        if blockchain == 'mo':
            return get_mo_wallet_transactions(wallet_address, from_block, to_block)  # MoChain transactions
        elif blockchain == 'bnb':
            # Add support for Binance Smart Chain (example):
            url = f'https://api.bscscan.com/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={BSCSCAN_API_KEY}'
            response = requests.get(url)
            data = response.json()
            return data.get('result', [])
        else:
            print(f"Unsupported blockchain: {blockchain}")
            raise ValueError('Invalid blockchain specified')
    except Exception as e:
        print(f"Error fetching wallet transactions: {e}")
        return []

# Function to send notifications via Telegram
def send_telegram_notification(message, value, usd_value, tx_hash, blockchain, chat_id):
    try:
        etherscan_link = f'<a href="https://mainnet.mochain.app/tx/{tx_hash}">MoChain Explorer</a>'
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': f'{chat_id}',
            'text': f'{message}: {etherscan_link}\nValue: {value:.6f} {blockchain.upper()} (${usd_value:.2f})',
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telegram notification sent with message: {message}, value: {value} {blockchain.upper()} (${usd_value:.2f}) to chat_id {chat_id}")
        return response
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return None

# Function to handle the /start command
def start(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_chat_ids[user_id] = chat_id  # Save the user's chat ID
    message = """
👋 Welcome to the Ethereum, Binance, and MoChain Wallet Monitoring Bot!

Use /add <blockchain> <wallet_address> to add a new wallet to monitor.

Example: /add ETH/BNB/MO <wallet_address>

Use /remove <blockchain> <wallet_address> to stop monitoring a wallet.

Example: /remove ETH/BNB/MO <wallet_address>

Use /list <blockchain> to list all wallets being monitored for a specific blockchain.

Example: /list ETH/BNB/MO or just /list
    """
    context.bot.send_message(chat_id=chat_id, text=message)

# Function to handle the /add command
def add_wallet(update, context):
    chat_id = update.message.chat_id
    if len(context.args) < 2:
        context.bot.send_message(chat_id=chat_id, text="Please provide a blockchain and wallet address to add.\nUsage: /add ETH/BNB/MO <wallet_address>")
        return

    blockchain = context.args[0].lower()
    wallet_address = context.args[1]

    # Support for MoChain and Binance Smart Chain
    if blockchain not in ['mo', 'bnb']:
        context.bot.send_message(chat_id=chat_id, text="Unsupported blockchain. Currently supported: MO, BNB")
        return

    # Add the wallet to the monitoring list
    watched_wallets.add(f"{blockchain}:{wallet_address}")
    save_watched_wallets()  # Save to file
    message = f"Added {wallet_address} on {blockchain.upper()} to the monitored wallets."
    context.bot.send_message(chat_id=chat_id, text=message)

# Function to handle the /remove command
def remove_wallet(update, context):
    chat_id = update.message.chat_id
    if len(context.args) < 2:
        context.bot.send_message(chat_id=chat_id, text="Please provide a blockchain and wallet address to remove.\nUsage: /remove ETH/BNB/MO <wallet_address>")
        return

    blockchain = context.args[0].lower()
    wallet_address = context.args[1]

    # Remove the wallet from the monitoring list
    wallet_to_remove = f"{blockchain}:{wallet_address}"
    if wallet_to_remove in watched_wallets:
        watched_wallets.remove(wallet_to_remove)
        save_watched_wallets()  # Save changes to file
        message = f"Removed {wallet_address} on {blockchain.upper()} from the monitored wallets."
    else:
        message = f"{wallet_address} on {blockchain.upper()} is not being monitored."
    
    context.bot.send_message(chat_id=chat_id, text=message)

# Function to handle the /list command
def list_wallets(update, context):
    chat_id = update.message.chat_id
    if watched_wallets:
        message = "Currently monitored wallets:\n"
        for wallet in watched_wallets:
            message += f"- {wallet}\n"
    else:
        message = "No wallets are being monitored."
    
    context.bot.send_message(chat_id=chat_id, text=message)

# Start monitoring in a separate thread (transaction monitoring)
def start_monitoring():
    monitor_thread = threading.Thread(target=monitor_wallets)
    monitor_thread.daemon = True
    monitor_thread.start()

# Main function for monitoring transactions
# Main function for monitoring transactions
# Minimum transaction value in MO to send a notification
MINIMUM_TRANSACTION_VALUE = 0.01  # Adjust this threshold as needed

# Main function for monitoring transactions
def monitor_wallets():
    last_checked_block = get_last_checked_block()
    web3 = Web3(Web3.HTTPProvider(MOCHAIN_RPC_URL))

    while True:
        latest_block = web3.eth.block_number

        if latest_block > last_checked_block:
            for wallet in watched_wallets:
                blockchain, wallet_address = wallet.split(':')
                
                # Fetch transactions only for the specific wallet being monitored
                transactions = get_wallet_transactions(wallet_address, blockchain, last_checked_block + 1, latest_block)

                for tx in transactions:
                    # Process transactions only if they involve the monitored wallet
                    if tx['from'].lower() == wallet_address.lower() or tx['to'].lower() == wallet_address.lower():
                        # Transaction processing
                        value = float(tx['value']) / 10**18  # Convert from wei to MO (assuming 18 decimals)
                        
                        # Filter out transactions with very small values
                        if value >= MINIMUM_TRANSACTION_VALUE:
                            tx_hash = tx['hash']
                            usd_value = value * 0.5  # Approximate USD value (use API for exact rate)
                            
                            # Send notification to all users monitoring the wallet
                            for chat_id in user_chat_ids.values():
                                send_telegram_notification("New transaction detected", value, usd_value, tx_hash, blockchain, chat_id)

            # Update the last checked block
            save_last_checked_block(latest_block)
        
        time.sleep(60)  # Check every 60 seconds

# Function to send notifications via Telegram (Updated for MO)
def send_telegram_notification(message, value, usd_value, tx_hash, blockchain, chat_id):
    try:
        if blockchain == 'mo':
            explorer_link = f'<a href="https://mainnet.mochain.app/tx/{tx_hash}">MoChain Explorer</a>'
        else:
            explorer_link = f'<a href="https://bscscan.com/tx/{tx_hash}">BscScan</a>'  # For BNB

        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': f'{chat_id}',
            'text': f'{message}: {explorer_link}\nValue: {value:.6f} MO (${usd_value:.2f})',
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telegram notification sent with message: {message}, value: {value} MO (${usd_value:.2f}) to chat_id {chat_id}")
        return response
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return None

# Main function to start the Telegram bot
def main():
    load_watched_wallets()  # Load wallets at startup
    start_monitoring()

    # Initialize the bot
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('add', add_wallet))
    dispatcher.add_handler(CommandHandler('remove', remove_wallet))
    dispatcher.add_handler(CommandHandler('list', list_wallets))

    # Start the bot
    updater.start_polling()
    updater.idle()  # Keep the bot running

if __name__ == '__main__':
    main()
