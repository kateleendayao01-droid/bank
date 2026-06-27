import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Database Setup
def init_db():
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, first_name TEXT, username TEXT, balance REAL, last_updated TEXT)''')
    conn.commit()
    conn.close()

def get_timestamp():
    return datetime.now().strftime("%B %d, %Y %I:%M %p")

# Command Handlers
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a user's message to create their account.")
        return
    
    user = update.message.reply_to_message.from_user
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)", 
              (str(user.id), user.first_name, user.username, 0.0, get_timestamp()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Account successfully created for {user.first_name}")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or len(context.args) < 1:
        await update.message.reply_text("Usage: /add [amount] [activity] (Reply to user)")
        return
    
    target = update.message.reply_to_message.from_user
    amount = float(context.args[0])
    activity = " ".join(context.args[1:]) or "."
    
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ?, last_updated = ? WHERE id = ?", 
              (amount, get_timestamp(), str(target.id)))
    c.execute("SELECT balance FROM users WHERE id = ?", (str(target.id),))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"Added ₱{amount:,.2f} to {target.first_name}.\nCurrent Balance: ₱{new_bal:,.2f}\nActivity: {activity}")

async def deduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or len(context.args) < 1:
        await update.message.reply_text("Usage: /deduct [amount] [activity] (Reply to user)")
        return
    
    target = update.message.reply_to_message.from_user
    amount = float(context.args[0])
    activity = " ".join(context.args[1:]) or "."
    
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance - ?, last_updated = ? WHERE id = ?", 
              (amount, get_timestamp(), str(target.id)))
    c.execute("SELECT balance FROM users WHERE id = ?", (str(target.id),))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"Deducted ₱{amount:,.2f} from {target.first_name}.\nCurrent Balance: ₱{new_bal:,.2f}\nActivity: {activity}")

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or len(context.args) < 1:
        await update.message.reply_text("Usage: /transfer [amount] (Reply to recipient)")
        return
    
    sender = update.message.from_user
    recipient = update.message.reply_to_message.from_user
    amount = float(context.args[0])
    
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id = ?", (str(sender.id),))
    sender_bal = c.fetchone()
    
    if not sender_bal or sender_bal[0] < amount:
        await update.message.reply_text("Insufficient funds.")
    else:
        c.execute("UPDATE users SET balance = balance - ?, last_updated = ? WHERE id = ?", (amount, get_timestamp(), str(sender.id)))
        c.execute("UPDATE users SET balance = balance + ?, last_updated = ? WHERE id = ?", (amount, get_timestamp(), str(recipient.id)))
        conn.commit()
        await update.message.reply_text(f"Transferred ₱{amount:,.2f} to {recipient.first_name}.\nYour New Balance: ₱{(sender_bal[0] - amount):,.2f}")
    conn.close()

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    conn = sqlite3.connect('bank.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (str(user.id),))
    data = c.fetchone()
    conn.close()
    
    if data:
        msg = (f"[  Member Information ]\nID: {data[0]}\nFirst name: {data[1]}\nUsername: {data[2]}\n"
               f"Permanent Link: [Profile](tg://user?id={data[0]})\n\n"
               f"[  Economy Information ]\nStatus: Active\nBranch: Bank by Kitsune\n"
               f"Amount (PHP): ₱{data[3]:,.2f}\nLast updated: {data[4]}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("Account not found. Use /create to register.")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('create', create))
    app.add_handler(CommandHandler('add', add))
    app.add_handler(CommandHandler('deduct', deduct))
    app.add_handler(CommandHandler('transfer', transfer))
    app.add_handler(CommandHandler('bank', bank))
    app.run_polling()
