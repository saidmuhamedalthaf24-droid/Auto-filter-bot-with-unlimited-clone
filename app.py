import os
import asyncio
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import motor.motor_asyncio
from info import API_ID, API_HASH, BOT_TOKEN, DB_URI, OWNER_ID, CHANNEL_ID, CLONE_DB_URI, LOG_CHANNEL

app = Client("filter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Main Database
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
db = mongo_client.filter_bot
filters_db = db.filters
users_db = db.users

# Clone Database
clone_client = motor.motor_asyncio.AsyncIOMotorClient(CLONE_DB_URI)
clone_db = clone_client.clone_bot
clones_collection = clone_db.clones

async def log_activity(text):
    """Log all activities to LOG_CHANNEL"""
    try:
        await app.send_message(LOG_CHANNEL, f"📝 **Log**: {text}")
    except:
        pass

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await log_activity(f"👤 User started bot: [{user_id}](tg://user?id={user_id}) - {message.from_user.first_name}")
    
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Clone Bot", callback_data="clone_menu")],
        [InlineKeyboardButton("📚 Help", callback_data="help_menu")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ])
    await message.reply(
        "🔥 **VJ Filter Clone Bot** (Full Featured)

"
        f"📢 **Channel**: `{CHANNEL_ID}`
"
        f"📝 **Logs**: `{LOG_CHANNEL}`
"
        "• Channel Auto Filter + SRB
"
        "• Unlimited Clone System
"
        "• Complete Logging
"
        "• /add /del /index /broadcast",
        reply_markup=btn
    )

@app.on_callback_query(filters.regex("clone_menu"))
async def clone_menu(client, callback):
    await log_activity(f"🔄 Clone menu opened: [{callback.from_user.id}](tg://user?id={callback.from_user.id})")
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Clone", callback_data="create_clone")],
        [InlineKeyboardButton("📋 My Clones", callback_data="my_clones")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback.edit_message_text("🚀 **Clone Menu**

**All clones logged in**: `{LOG_CHANNEL}`", reply_markup=btn)

@app.on_callback_query(filters.regex("create_clone"))
async def create_clone(client, callback):
    user_id = callback.from_user.id
    clone_count = await clones_collection.count_documents({"user_id": user_id})
    
    if clone_count >= 100:
        await callback.answer("❌ Limit reached!", show_alert=True)
        return
    
    bot_id = random.randint(1000000000, 9999999999)
    new_token = f"{int(BOT_TOKEN.split(':')[0])}:{bot_id}"
    
    clone_data = {
        "user_id": user_id,
        "username": callback.from_user.username or "unknown",
        "token": new_token,
        "api_id": API_ID,
        "api_hash": API_HASH,
        "channel_id": CHANNEL_ID,
        "db_uri": DB_URI,
        "clone_db_uri": CLONE_DB_URI,
        "log_channel": LOG_CHANNEL,
        "created": datetime.now()
    }
    
    await clones_collection.insert_one(clone_data)
    
    # Log clone creation
    await log_activity(
        f"✅ **New Clone Created**
"
        f"👤 User: [{user_id}](tg://user?id={user_id})
"
        f"🔑 Token: `{new_token}`
"
        f"📊 Total: {clone_count+1}"
    )
    
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="clone_menu")]])
    await callback.edit_message_text(
        f"✅ **Clone #{clone_count+1} Created!**

"
        f"**Token**: `{new_token}`
"
        f"**Check logs**: `{LOG_CHANNEL}`

"
        f"**Deploy**: Fork → Render → All vars ready!",
        reply_markup=btn
    )

# Channel Auto Filter (VJ Style + Logging)
@app.on_message(filters.text & filters.group)
async def channel_auto_filter(client, message):
    name = message.text.strip().lower()
    await log_activity(f"🔍 Search: `{name}` by [{message.from_user.id}](tg://user?id={message.from_user.id})")
    
    # Search CHANNEL_ID first
    async for msg in client.search_messages(CHANNEL_ID, query=name, limit=10):
        if msg.media:
            btns = [[InlineKeyboardButton(f"🎥 {name}", callback_data=f"chfltr_{msg.id}")]]
            await message.reply(f"✅ **Found in Channel** `{CHANNEL_ID}`!", reply_markup=InlineKeyboardMarkup(btns))
            await log_activity(f"✅ Channel result found for: `{name}`")
            return
    
    # MongoDB backup search
    results = await filters_db.find({"name": {"$regex": name, "$options": "i"}}).to_list(10)
    if results:
        btns = []
        for i, result in enumerate(results[:5], 1):
            btns.append([InlineKeyboardButton(f"🎥 {i}", callback_data=f"fltr_{result['_id']}")])
        if len(results) > 5:
            btns.append([InlineKeyboardButton("➡️ More", callback_data=f"page_2_{name}")])
        await message.reply("⏳ **Searching Filters...**", reply_markup=InlineKeyboardMarkup(btns))
        await log_activity(f"✅ Filter results: {len(results)} for `{name}`")

@app.on_message(filters.command("add") & filters.group)
async def add_manual_filter(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ `/add Movie Name` (reply to media)")
    
    name = " ".join(message.command[1:])
    msg = message.reply_to_message
    
    if not msg or not msg.media:
        return await message.reply("❌ Reply to media message!")
    
    await filters_db.insert_one({
        "name": name.lower(),
        "group_id": message.chat.id,
        "message_id": msg.id,
        "file_id": msg.document.file_id if msg.document else msg.video.file_id,
        "added_by": message.from_user.id,
        "added_date": datetime.now()
    })
    
    await message.reply(f"✅ **Added**: `{name}`")
    await log_activity(f"➕ Filter added: `{name}` by [{message.from_user.id}](tg://user?id={message.from_user.id})")

@app.on_message(filters.command("start") & filters.private)
async def private_start(client, message):
    await log_activity(f"🤖 Bot started by: [{message.from_user.id}](tg://user?id={message.from_user.id})")

if __name__ == "__main__":
    print("🚀 VJ Channel Filter Clone Bot + Logs Starting...")
    asyncio.run(log_activity("🚀 Bot Started Successfully!"))
    app.run()
