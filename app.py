import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo
from info import *

app = Client("filter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Connections
mongo_client = AsyncIOMotorClient(DB_URI)
db = mongo_client.filterbot
filters_db = db.filters
clone_db = AsyncIOMotorClient(CLONE_DB_URI)["clonebot"]["clones"]

CHANNEL_ID = int(CHANNEL_ID)
LOG_CHANNEL = int(LOG_CHANNEL)

btn = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ Add Filter", callback_data="add_filter")],
    [InlineKeyboardButton("🔄 Clone Bot", callback_data="clone_bot")]
])

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "🔥 **VJ Filter Clone Bot** (Full Featured)",
        reply_markup=btn
    )

@app.on_callback_query(filters.regex("add_filter"))
async def add_filter(client, callback):
    await callback.message.edit_text(
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
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Add Filter", callback_data="add_manual")]
        ])
    )

@app.on_message(filters.command("add") & filters.private)
async def add_filter_cmd(client, message):
    await message.reply_text("Send: /add Movie Name | Message ID")

@app.on_message(filters.private & filters.text)
async def handle_filter_search(client, message):
    name = message.text
    filters_list = await filters_db.find({"name": {"$regex": name, "$options": "i"}}).to_list(length=10)
    
    if not filters_list:
        await message.reply_text("❌ No results found!")
        return
    
    buttons = []
    for flt in filters_list:
        btn = InlineKeyboardButton(
            f"🎥 {flt['name']}", 
            callback_data=f"show_{flt['_id']}"
        )
        buttons.append([btn])
    
    await message.reply_text(
        f"✅ **{len(filters_list)} results found:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"show_(.+)"))
async def show_filter(client, callback):
    flt_id = callback.data.split("_")[1]
    fltr = await filters_db.find_one({"_id": int(flt_id)})
    
    if not fltr:
        await callback.answer("Filter not found!")
        return
    
    btn = InlineKeyboardButton("🎥 Get Movie", url=f"https://t.me/{(await app.get_me()).username}?start=msg_{fltr['msg_id']}")
    
    await callback.message.edit_text(
        f"🎬 **{fltr['name']}**

{fltr.get('desc', '')}",
        reply_markup=InlineKeyboardMarkup([[btn]])
    )

# Clone Bot System
@app.on_callback_query(filters.regex("clone_bot"))
async def clone_menu(client, callback):
    user_id = callback.from_user.id
    clones = await clone_db.find({"user_id": user_id}).to_list(length=100)
    
    text = f"🤖 **Your Clones: {len(clones)}/100**

"
    buttons = []
    
    for clone in clones[-5:]:  # Last 5 clones
        btn = InlineKeyboardButton(
            f"🔗 {clone['token'][:20]}...", 
            callback_data=f"manage_clone_{clone['_id']}"
        )
        buttons.append([btn])
    
    buttons.append([InlineKeyboardButton("➕ New Clone", callback_data="new_clone")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("new_clone"))
async def new_clone(client, callback):
    user_id = callback.from_user.id
    count = await clone_db.count_documents({"user_id": user_id})
    
    if count >= 100:
        await callback.answer("❌ Max 100 clones reached!")
        return
    
    new_token = f"CLONE_{user_id}_{count+1}"
    await clone_db.insert_one({
        "user_id": user_id,
        "token": new_token,
        "created": asyncio.get_event_loop().time()
    })
    
    await callback.answer("✅ New clone created!")

# Channel Filter Forwarding
@app.on_message(filters.channel & filters.incoming)
async def auto_filter(client, message):
    if message.chat.id != CHANNEL_ID:
        return
    
    msg_id = message.id
    caption = message.caption or ""
    
    # Extract movie names (simple regex)
    import re
    movies = re.findall(r'([A-Z][a-zA-Zs&]{2,50})(?:s*(|[|||$)', caption, re.IGNORECASE)
    
    for movie in movies[:3]:  # Max 3 filters per message
        await filters_db.update_one(
            {"name": movie.strip()},
            {"$set": {
                "msg_id": msg_id,
                "desc": caption,
                "updated": asyncio.get_event_loop().time()
            }},
            upsert=True
        )
        
        # Log
        log_msg = f"**New Filter Added**
🎬 `{movie.strip()}`
📱 Msg: {msg_id}"
        try:
            await client.send_message(LOG_CHANNEL, log_msg)
        except:
            pass

print("🚀 Bot Started Successfully!")
app.run()
