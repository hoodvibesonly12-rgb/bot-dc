import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import json
import os
import re
from datetime import datetime, timedelta

# ========================
#        KONFIGURACJA
# ========================
TOKEN = os.getenv(MTQ4NTIzMzkyMDc1OTgyODU5MA.GwLyuP.aLADGn-vsEgu9ohfDCfzk5-tmlCDPWa58EzJZc)
GUILD_ID = 1476578879618547805

# Kanały
WELCOME_CHANNEL = "👋 | witam"
ANNOUNCEMENT_CHANNEL = "📢 | ogłoszenia"
LOG_CHANNEL = "📋 | logi"  # opcjonalnie możesz stworzyć

# YouTube
YT_CHANNEL_ID = "PHILIPPE-SCOUTINHO"  # zostanie sprawdzone przez API
YT_API_KEY = os.getenv("YT_API_KEY")  # dodaj w Railway

# Kick
KICK_USERNAME = "deziszponcicel"

# Role
NEW_MEMBER_ROLE = "gracz"

# Auto-mod - wulgaryzmy (możesz rozszerzyć listę)
BANNED_WORDS = ["chuj", "kurwa", "jebać", "pierdol", "skurwysyn", "👿"]

# ========================
#      SETUP BOTA
# ========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Pamięć podręczna
last_yt_video_id = None
kick_was_live = False
active_giveaways = {}  # message_id -> dane giveawaya


# ========================
#        HELPERS
# ========================
async def get_channel_by_name(guild, name):
    return discord.utils.get(guild.channels, name=name)


async def get_or_create_role(guild, role_name):
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        role = await guild.create_role(name=role_name, color=discord.Color.blue())
    return role


# ========================
#      ON READY
# ========================
@bot.event
async def on_ready():
    print(f"✅ Bot zalogowany jako {bot.user}")
    check_youtube.start()
    check_kick.start()
    print("📡 Sprawdzanie YouTube i Kick uruchomione")


# ========================
#    POWITANIA + ROLA
# ========================
@bot.event
async def on_member_join(member):
    guild = member.guild

    # Nadaj rolę gracz
    role = await get_or_create_role(guild, NEW_MEMBER_ROLE)
    try:
        await member.add_roles(role)
    except:
        pass

    # Wyślij powitanie
    channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL.replace("# ", "").strip())
    if channel:
        embed = discord.Embed(
            title=f"👋 Witaj na serwerze, {member.display_name}!",
            description=(
                f"Hej {member.mention}, dobrze że jesteś! 🎮\n\n"
                f"📋 Sprawdź regulamin zanim zaczniesz\n"
                f"🎯 Dostałeś rolę **{NEW_MEMBER_ROLE}** automatycznie\n"
                f"💬 Śmiało pisz na kanałach tekstowych!\n\n"
                f"Jesteś naszym **{guild.member_count}**. członkiem! 🔥"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=guild.name)
        await channel.send(embed=embed)

    # Logi
    log_ch = discord.utils.get(guild.text_channels, name="logi")
    if log_ch:
        await log_ch.send(f"➕ `{member}` dołączył do serwera — {datetime.now().strftime('%d.%m.%Y %H:%M')}")


@bot.event
async def on_member_remove(member):
    guild = member.guild
    log_ch = discord.utils.get(guild.text_channels, name="logi")
    if log_ch:
        await log_ch.send(f"➖ `{member}` opuścił serwer — {datetime.now().strftime('%d.%m.%Y %H:%M')}")


# ========================
#      AUTO-MODERACJA
# ========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    for word in BANNED_WORDS:
        if word in content_lower:
            await message.delete()
            warn = await message.channel.send(
                f"⚠️ {message.author.mention} — uważaj na słownictwo! Wiadomość została usunięta."
            )
            await asyncio.sleep(5)
            await warn.delete()
            return

    await bot.process_commands(message)


# ========================
#    KOMENDA !setup
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    await ctx.send("⚙️ Tworzę kanały i kategorie... chwila!")

    # Definicja struktury
    struktura = {
        "🏠 | lobby": [
            ("tekst", "👋 | witam"),
            ("tekst", "📋 | regulamin"),
        ],
        "📁 Informacje": [
            ("tekst", "📢 | ogłoszenia"),
            ("tekst", "🌐 | social-media"),
            ("tekst", "🥇 | konkursy"),
            ("tekst", "👥 | zaproszenia"),
        ],
        "📁 Tekstowe": [
            ("tekst", "💬 | ogólny"),
            ("tekst", "📺 | odcinki"),
            ("tekst", "🎬 | klipy"),
            ("tekst", "💰 | csgoskins"),
            ("tekst", "💰 | casehug"),
            ("tekst", "✅ | legitcheck"),
        ],
        "─── 「GŁOSOWE」───": [
            ("głos", "LIGA"),
            ("głos", "FACEIT"),
            ("głos", "PREMIER"),
            ("głos", "FIFA"),
            ("głos", "OGÓLNY"),
            ("głos", "OGÓLNYV2"),
        ],
        "「Administration」": [
            ("tekst", "🔧 | czat-administracji"),
            ("tekst", "🔒 | komendy-administracji"),
            ("tekst", "logi"),
        ],
    }

    for cat_name, channels in struktura.items():
        # Sprawdź czy kategoria istnieje
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)

        for typ, ch_name in channels:
            existing = discord.utils.get(guild.channels, name=ch_name)
            if not existing:
                if typ == "tekst":
                    await guild.create_text_channel(ch_name, category=category)
                else:
                    await guild.create_voice_channel(ch_name, category=category)

    await ctx.send("✅ Gotowe! Wszystkie kanały zostały utworzone.")


# ========================
#    GIVEAWAY
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, days: int, *, nagroda: str):
    """Użycie: !giveaway 2 Skin CS2"""
    end_time = datetime.now() + timedelta(days=days)

    embed = discord.Embed(
        title="🎉 GIVEAWAY!",
        description=(
            f"**Nagroda:** {nagroda}\n\n"
            f"Dodaj reakcję 🎉 żeby wziąć udział!\n\n"
            f"⏰ Kończy się: **{end_time.strftime('%d.%m.%Y o %H:%M')}**\n"
            f"Czas trwania: **{days} {'dzień' if days == 1 else 'dni'}**"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Organizator: {ctx.author.display_name}")

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    active_giveaways[msg.id] = {
        "nagroda": nagroda,
        "end_time": end_time,
        "channel_id": ctx.channel.id,
        "days_left": days
    }

    # Uruchom odliczanie
    bot.loop.create_task(countdown_giveaway(msg.id, ctx.guild))


async def countdown_giveaway(msg_id, guild):
    while msg_id in active_giveaways:
        data = active_giveaways[msg_id]
        now = datetime.now()

        if now >= data["end_time"]:
            # Zakończ giveaway
            channel = guild.get_channel(data["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(msg_id)
                    reaction = discord.utils.get(msg.reactions, emoji="🎉")
                    if reaction:
                        users = [u async for u in reaction.users() if not u.bot]
                        if users:
                            import random
                            winner = random.choice(users)
                            await channel.send(
                                f"🏆 Gratulacje {winner.mention}! Wygrałeś **{data['nagroda']}**! 🎉"
                            )
                        else:
                            await channel.send("😢 Nikt nie wziął udziału w giveawayu...")
                except:
                    pass
            del active_giveaways[msg_id]
            break

        # Aktualizuj embed co godzinę
        await asyncio.sleep(3600)
        if msg_id not in active_giveaways:
            break

        time_left = data["end_time"] - datetime.now()
        hours_left = int(time_left.total_seconds() // 3600)
        days_left = time_left.days

        channel = guild.get_channel(data["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = msg.embeds[0]
                embed.description = (
                    f"**Nagroda:** {data['nagroda']}\n\n"
                    f"Dodaj reakcję 🎉 żeby wziąć udział!\n\n"
                    f"⏰ Kończy się: **{data['end_time'].strftime('%d.%m.%Y o %H:%M')}**\n"
                    f"Pozostało: **{days_left}d {hours_left % 24}h**"
                )
                await msg.edit(embed=embed)
            except:
                pass


# ========================
#   YOUTUBE POWIADOMIENIA
# ========================
@tasks.loop(minutes=10)
async def check_youtube():
    global last_yt_video_id
    if not YT_API_KEY:
        return

    try:
        async with aiohttp.ClientSession() as session:
            # Pobierz ID kanału
            search_url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?key={YT_API_KEY}&channelId={await get_yt_channel_id(session)}"
                f"&part=snippet&order=date&maxResults=1&type=video"
            )
            async with session.get(search_url) as resp:
                data = await resp.json()

            if not data.get("items"):
                return

            latest = data["items"][0]
            video_id = latest["id"]["videoId"]

            if video_id == last_yt_video_id:
                return

            last_yt_video_id = video_id
            title = latest["snippet"]["title"]
            url = f"https://youtu.be/{video_id}"
            thumbnail = latest["snippet"]["thumbnails"]["high"]["url"]

            guild = bot.get_guild(GUILD_ID)
            if not guild:
                return

            channel = discord.utils.get(guild.text_channels, name="📢 | ogłoszenia")
            if channel:
                embed = discord.Embed(
                    title=f"🎬 Nowy filmik na YouTube!",
                    description=f"**{title}**\n\n🔗 {url}",
                    color=discord.Color.red()
                )
                embed.set_image(url=thumbnail)
                embed.set_footer(text="YouTube • PHILIPPE-SCOUTINHO")
                await channel.send("@everyone 🎬 Nowy film już jest!", embed=embed)

    except Exception as e:
        print(f"[YT Error] {e}")


async def get_yt_channel_id(session):
    url = (
        f"https://www.googleapis.com/youtube/v3/channels"
        f"?key={YT_API_KEY}&forHandle=PHILIPPE-SCOUTINHO&part=id"
    )
    async with session.get(url) as resp:
        data = await resp.json()
    return data["items"][0]["id"] if data.get("items") else None


# ========================
#   KICK POWIADOMIENIA
# ========================
@tasks.loop(minutes=3)
async def check_kick():
    global kick_was_live
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://kick.com/api/v1/channels/{KICK_USERNAME}"
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return
                data = await resp.json()

        is_live = data.get("livestream") is not None

        if is_live and not kick_was_live:
            kick_was_live = True
            stream = data["livestream"]
            title = stream.get("session_title", "Stream na żywo!")
            viewers = stream.get("viewer_count", 0)
            thumbnail = stream.get("thumbnail", {}).get("url", "")

            guild = bot.get_guild(GUILD_ID)
            if not guild:
                return

            channel = discord.utils.get(guild.text_channels, name="📢 | ogłoszenia")
            if channel:
                embed = discord.Embed(
                    title="🔴 LIVE na Kick!",
                    description=(
                        f"**{title}**\n\n"
                        f"👥 Widzów: **{viewers}**\n"
                        f"🔗 https://kick.com/{KICK_USERNAME}"
                    ),
                    color=discord.Color.green()
                )
                if thumbnail:
                    embed.set_image(url=thumbnail)
                embed.set_footer(text="Kick.com • deziszponcicel")
                await channel.send("@everyone 🔴 Jesteśmy na żywo!", embed=embed)

        elif not is_live:
            kick_was_live = False

    except Exception as e:
        print(f"[Kick Error] {e}")


# ========================
#      URUCHOM BOTA
# ========================
bot.run(TOKEN)
