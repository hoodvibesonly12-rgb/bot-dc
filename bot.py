import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import os
import random
from datetime import datetime, timedelta
import pytz

# ========================
#      KONFIGURACJA
# ========================
TOKEN = os.getenv("DISCORD_TOKEN")
YT_API_KEY = os.getenv("YT_API_KEY")
GUILD_ID = 1476578879618547805
KICK_USERNAME = "deziszponcicel"
YT_HANDLE = "PHILIPPE-SCOUTINHO"
WARSAW_TZ = pytz.timezone("Europe/Warsaw")

# Kanały
WELCOME_CHANNEL = "👋 | witam"
ANNOUNCE_CHANNEL = "📢 | ogłoszenia"
LOG_CHANNEL = "logi"
TEMP_VC_CATEGORY = "🔊 Kanały tymczasowe"

# Wulgaryzmy
BANNED_WORDS = ["chuj", "kurwa", "jebać", "pierdol", "skurwysyn"]

# Rola nowych
NEW_MEMBER_ROLE = "gracz"

# ========================
#      SETUP BOTA
# ========================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Pamięć
last_yt_video_id = None
kick_was_live = False
active_giveaways = {}
temp_voice_channels = {}  # channel_id -> owner_id


# ========================
#        ON READY
# ========================
@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")
    check_youtube.start()
    check_kick.start()
    update_stats.start()


# ========================
#   POWITANIA + ROLA
# ========================
@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=NEW_MEMBER_ROLE)
    if not role:
        role = await guild.create_role(name=NEW_MEMBER_ROLE, color=discord.Color.blue())
    try:
        await member.add_roles(role)
    except:
        pass

    ch = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL.replace("# ", "").strip())
    if ch:
        embed = discord.Embed(
            title=f"👋 Witaj, {member.display_name}!",
            description=(
                f"Hej {member.mention}, cieszymy się że jesteś! 🎮\n\n"
                f"📋 Sprawdź regulamin\n"
                f"🎯 Dostałeś rolę **{NEW_MEMBER_ROLE}** automatycznie\n"
                f"💬 Śmiało pisz na kanałach!\n\n"
                f"Jesteś naszym **{guild.member_count}**. członkiem! 🔥"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ch.send(embed=embed)

    log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
    if log_ch:
        now = datetime.now(WARSAW_TZ).strftime("%d.%m.%Y %H:%M")
        await log_ch.send(f"➕ `{member}` dołączył — {now}")


@bot.event
async def on_member_remove(member):
    log_ch = discord.utils.get(member.guild.text_channels, name=LOG_CHANNEL)
    if log_ch:
        now = datetime.now(WARSAW_TZ).strftime("%d.%m.%Y %H:%M")
        await log_ch.send(f"➖ `{member}` opuścił serwer — {now}")


# ========================
#   NITRO BOOST LOG
# ========================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        log_ch = discord.utils.get(after.guild.text_channels, name=LOG_CHANNEL)
        if log_ch:
            await log_ch.send(f"💜 {after.mention} właśnie dał **Nitro Boost** serwerowi! Dziękujemy! 🚀")
        ann = discord.utils.get(after.guild.text_channels, name=ANNOUNCE_CHANNEL)
        if ann:
            await ann.send(f"💜 Wielkie podziękowania dla {after.mention} za **Nitro Boost**! 🎉")


# ========================
#    AUTO-MODERACJA
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
                f"⚠️ {message.author.mention} — uważaj na słownictwo! Wiadomość usunięta."
            )
            await asyncio.sleep(5)
            await warn.delete()
            return
    await bot.process_commands(message)


# ========================
#  KANAŁY TYMCZASOWE (VC)
# ========================
@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild

    # Wejście na kanał "➕ Utwórz kanał"
    trigger = discord.utils.get(guild.voice_channels, name="➕ Utwórz kanał")
    if after.channel and trigger and after.channel.id == trigger.id:
        category = discord.utils.get(guild.categories, name=TEMP_VC_CATEGORY)
        if not category:
            category = await guild.create_category(TEMP_VC_CATEGORY)
        new_vc = await guild.create_voice_channel(
            f"🎮 {member.display_name}",
            category=category
        )
        await member.move_to(new_vc)
        temp_voice_channels[new_vc.id] = member.id

    # Usuwanie pustych kanałów tymczasowych
    if before.channel and before.channel.id in temp_voice_channels:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                del temp_voice_channels[before.channel.id]
            except:
                pass


# ========================
#   STATYSTYKI (auto-update)
# ========================
@tasks.loop(minutes=10)
async def update_stats():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    now = datetime.now(WARSAW_TZ).strftime("%H:%M")
    members = guild.member_count
    boosters = guild.premium_subscription_count or 0

    # Kanały statystyk w kategorii
    stats = {
        f"🕐 Warszawa: {now}": "czas-warszawa",
        f"👥 Członków: {members}": "liczba-czlonkow",
        f"💜 Nitro: {boosters}": "nitro-boosty",
    }

    cat = discord.utils.get(guild.categories, name="📊 Statystyki")
    if not cat:
        cat = await guild.create_category("📊 Statystyki")

    for display_name, base_name in stats.items():
        existing = discord.utils.get(guild.voice_channels, name__startswith=base_name.split(":")[0].strip())
        # Znajdź kanał z podobną nazwą
        found = None
        for ch in cat.voice_channels:
            if base_name.split("-")[0] in ch.name.lower().replace(" ", "-"):
                found = ch
                break
        if found:
            try:
                await found.edit(name=display_name)
            except:
                pass
        else:
            try:
                vc = await guild.create_voice_channel(display_name, category=cat)
                await vc.set_permissions(guild.default_role, connect=False)
            except:
                pass


# ========================
#    KOMENDA !godzina
# ========================
@bot.command()
async def godzina(ctx):
    now = datetime.now(WARSAW_TZ).strftime("%H:%M:%S")
    date = datetime.now(WARSAW_TZ).strftime("%d.%m.%Y")
    embed = discord.Embed(
        title="🕐 Czas w Warszawie",
        description=f"**{now}**\n📅 {date}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


# ========================
#    KOMENDA !statsy
# ========================
@bot.command()
async def statsy(ctx):
    guild = ctx.guild
    boosters = [m for m in guild.members if m.premium_since]
    embed = discord.Embed(title=f"📊 Statystyki — {guild.name}", color=discord.Color.purple())
    embed.add_field(name="👥 Członkowie", value=str(guild.member_count), inline=True)
    embed.add_field(name="💜 Nitro Boosterów", value=str(len(boosters)), inline=True)
    embed.add_field(name="🕐 Czas (Warszawa)", value=datetime.now(WARSAW_TZ).strftime("%H:%M"), inline=True)
    if boosters:
        embed.add_field(
            name="💜 Boosterzy",
            value="\n".join([m.mention for m in boosters[:10]]),
            inline=False
        )
    await ctx.send(embed=embed)


# ========================
#    KOMENDA !stream
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def stream(ctx, *, tytul: str = "Stream na żywo!"):
    ann = discord.utils.get(ctx.guild.text_channels, name=ANNOUNCE_CHANNEL)
    target = ann or ctx.channel
    embed = discord.Embed(
        title="🔴 JESTEŚMY NA ŻYWO!",
        description=(
            f"**{tytul}**\n\n"
            f"🎮 Dołącz teraz!\n"
            f"🔗 https://kick.com/{KICK_USERNAME}"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Kick.com • deziszponcicel")
    await target.send("@everyone 🔴 Stream wystartował!", embed=embed)
    if target != ctx.channel:
        await ctx.message.add_reaction("✅")


# ========================
#    KOMENDA !giveaway
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, days: int, winners: int, *, nagroda: str):
    """Użycie: !giveaway <dni> <liczba_zwycięzców> <nagroda>
    Przykład: !giveaway 2 3 Skin CS2"""
    end_time = datetime.now(WARSAW_TZ) + timedelta(days=days)

    embed = discord.Embed(
        title="🎉 GIVEAWAY!",
        description=(
            f"**Nagroda:** {nagroda}\n\n"
            f"Dodaj reakcję 🎉 żeby wziąć udział!\n\n"
            f"🏆 Liczba zwycięzców: **{winners}**\n"
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
        "winners": winners,
        "days": days
    }
    bot.loop.create_task(countdown_giveaway(msg.id, ctx.guild))


async def countdown_giveaway(msg_id, guild):
    while msg_id in active_giveaways:
        data = active_giveaways[msg_id]
        now = datetime.now(WARSAW_TZ)

        if now >= data["end_time"]:
            channel = guild.get_channel(data["channel_id"])
            if channel:
                try:
                    msg = await channel.fetch_message(msg_id)
                    reaction = discord.utils.get(msg.reactions, emoji="🎉")
                    if reaction:
                        users = [u async for u in reaction.users() if not u.bot]
                        if users:
                            count = min(data["winners"], len(users))
                            winners = random.sample(users, count)
                            mentions = " ".join([w.mention for w in winners])
                            await channel.send(
                                f"🏆 Gratulacje {mentions}! {'Wygraliście' if count > 1 else 'Wygrałeś'} **{data['nagroda']}**! 🎉"
                            )
                        else:
                            await channel.send("😢 Nikt nie wziął udziału w giveawayu...")
                except:
                    pass
            del active_giveaways[msg_id]
            break

        # Aktualizuj co godzinę
        await asyncio.sleep(3600)
        if msg_id not in active_giveaways:
            break

        time_left = data["end_time"] - datetime.now(WARSAW_TZ)
        days_left = time_left.days
        hours_left = int(time_left.total_seconds() // 3600) % 24

        channel = guild.get_channel(data["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = msg.embeds[0]
                embed.description = (
                    f"**Nagroda:** {data['nagroda']}\n\n"
                    f"Dodaj reakcję 🎉 żeby wziąć udział!\n\n"
                    f"🏆 Liczba zwycięzców: **{data['winners']}**\n"
                    f"⏰ Kończy się: **{data['end_time'].strftime('%d.%m.%Y o %H:%M')}**\n"
                    f"Pozostało: **{days_left}d {hours_left}h**"
                )
                await msg.edit(embed=embed)
            except:
                pass


# ========================
#   MUZYKA (YT/Spotify)
# ========================
@bot.command()
async def play(ctx, *, url: str):
    if not ctx.author.voice:
        await ctx.send("❌ Musisz być na kanale głosowym!")
        return

    await ctx.send(
        "⚠️ **Odtwarzanie muzyki** wymaga dodatkowej biblioteki `yt-dlp` oraz `FFmpeg`.\n\n"
        "Aby włączyć muzykę na swoim serwerze polecam użyć gotowego bota muzycznego:\n"
        "🎵 **Hydra** — https://hydra.bot\n"
        "🎵 **Jockie** — https://jockie.music\n"
        "🎵 **Muse** — https://github.com/codetheweb/muse\n\n"
        "Są darmowe i obsługują YouTube oraz Spotify!"
    )


# ========================
#  KOMENDA !resetkanaly
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def resetkanaly(ctx):
    msg = await ctx.send("⚠️ Czy na pewno chcesz usunąć **WSZYSTKIE** kanały? Wpisz `tak` (masz 15 sekund).")

    def check(m):
        return m.author == ctx.author and m.content.lower() == "tak" and m.channel == ctx.channel

    try:
        await bot.wait_for("message", check=check, timeout=15.0)
    except asyncio.TimeoutError:
        await msg.edit(content="❌ Anulowano.")
        return

    await ctx.send("🗑️ Usuwam wszystkie kanały...")
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
        except:
            pass

    temp = await ctx.guild.create_text_channel("bot")
    await temp.send("✅ Gotowe! Wpisz `!setup` żeby odtworzyć kanały.")


# ========================
#    KOMENDA !setup
# ========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    await ctx.send("⚙️ Tworzę kanały... chwila!")

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
        "🔊 Kanały tymczasowe": [
            ("głos", "➕ Utwórz kanał"),
        ],
        "📊 Statystyki": [],
        "「Administration」": [
            ("tekst", "🔧 | czat-administracji"),
            ("tekst", "🔒 | komendy-administracji"),
            ("tekst", "logi"),
        ],
    }

    for cat_name, channels in struktura.items():
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        for typ, ch_name in channels:
            existing = discord.utils.get(guild.channels, name=ch_name)
            if not existing:
                if typ == "tekst":
                    await guild.create_text_channel(ch_name, category=category)
                else:
                    vc = await guild.create_voice_channel(ch_name, category=category)
                    if cat_name == "📊 Statystyki":
                        await vc.set_permissions(guild.default_role, connect=False)

    await ctx.send("✅ Gotowe! Wszystkie kanały zostały utworzone. Statystyki zaktualizują się za chwilę.")
    await update_stats()


# ========================
#   YOUTUBE POWIADOMIENIA
# ========================
@tasks.loop(minutes=10)
async def check_youtube():
    global last_yt_video_id
    if not YT_API_KEY or YT_API_KEY == "brak":
        return
    try:
        async with aiohttp.ClientSession() as session:
            ch_url = f"https://www.googleapis.com/youtube/v3/channels?key={YT_API_KEY}&forHandle={YT_HANDLE}&part=id"
            async with session.get(ch_url) as r:
                ch_data = await r.json()
            if not ch_data.get("items"):
                return
            yt_channel_id = ch_data["items"][0]["id"]

            search_url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?key={YT_API_KEY}&channelId={yt_channel_id}"
                f"&part=snippet&order=date&maxResults=1&type=video"
            )
            async with session.get(search_url) as r:
                data = await r.json()

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
            channel = discord.utils.get(guild.text_channels, name=ANNOUNCE_CHANNEL)
            if channel:
                embed = discord.Embed(
                    title="🎬 Nowy filmik na YouTube!",
                    description=f"**{title}**\n\n🔗 {url}",
                    color=discord.Color.red()
                )
                embed.set_image(url=thumbnail)
                embed.set_footer(text="YouTube • PHILIPPE-SCOUTINHO")
                await channel.send("@everyone 🎬 Nowy film już jest!", embed=embed)
    except Exception as e:
        print(f"[YT Error] {e}")


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
            channel = discord.utils.get(guild.text_channels, name=ANNOUNCE_CHANNEL)
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
