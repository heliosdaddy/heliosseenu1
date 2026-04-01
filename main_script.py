import asyncio
import aiohttp
import random

# ================= API ENDPOINTS =================
FEED_URL = "https://www.clubhouseapi.com/api/get_feed_v3"
JOIN_ROOM_URL = "https://www.clubhouseapi.com/api/join_channel"
LEAVE_ROOM_URL = "https://www.clubhouseapi.com/api/leave_channel"
ACTIVE_PING_URL = "https://www.clubhouseapi.com/api/active_ping"
AUDIENCE_REPLY_URL = "https://www.clubhouseapi.com/api/audience_reply"
MAKE_ME_SPEAKER_URL = "https://www.clubhouseapi.com/api/make_me_speaker"
INVITE_SPEAKER_URL = "https://www.clubhouseapi.com/api/invite_speaker"
USER_PROFILE_URL = "https://www.clubhouseapi.com/api/get_profile"
GET_CHANNEL_URL = "https://www.clubhouseapi.com/api/get_channel"
FOLLOW_USER_URL = "https://www.clubhouseapi.com/api/follow"
GIF_REACTION_URL = "https://www.clubhouseapi.com/api/gif_reaction"
SELF_PROFILE_URL = "https://www.clubhouseapi.com/api/me"

# ================= MULTIPLE ACCEPT SPEAKER INVITE URLS =================
ACCEPT_SPEAKER_INVITE_URLS = [
    "https://www.clubhouseapi.com/api/become_speaker",
    "https://www.clubhouseapi.com/api/accept_speaker_invite",
    "https://www.clubhouseapi.com/api/accept_invite",
]

# ================= CONFIG =================
FOLLOW_DELAY = 15
PING_DELAY = 15
GIF_MIN_DELAY = 3
GIF_MAX_DELAY = 6
INVITE_DELAY = 10
POLL_INTERVAL = 5

# ================= HEADERS =================
def get_headers(token, user_id):
    return {
        "Authorization": f"Token {token}",
        "CH-UserID": str(user_id),
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "CH-AppVersion": "1.0.9",
        "CH-AppBuild": "305",
    }

async def post(session, url, headers, data):
    try:
        async with session.post(url, headers=headers, json=data) as r:
            try:
                return r.status, await r.json(content_type=None)
            except:
                return r.status, {}
    except Exception as e:
        print(f"[ERROR] Request failed → {e}")
        return None, {}

# ================= LOAD TOKENS =================
async def fetch_user_id(session, token):
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }
    status, data = await post(session, SELF_PROFILE_URL, headers, {})
    if status == 200 and data:
        user_id = data.get("user_id") or data.get("id") or (data.get("user_profile") or {}).get("user_id")
        if user_id:
            return int(user_id)
    print(f"[ERROR] Could not fetch user_id for token {token[:8]}... (status {status})")
    return None

async def load_tokens():
    raw_bots = []
    with open("tokens.txt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                token, gifs_str = line.split("|", 1)
                gifs = [g.strip() for g in gifs_str.split(",") if g.strip()]
            else:
                token = line
                gifs = []
            raw_bots.append({"token": token.strip(), "gifs": gifs})

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_user_id(session, bot["token"]) for bot in raw_bots]
        user_ids = await asyncio.gather(*tasks)

    bots = []
    for bot, uid in zip(raw_bots, user_ids):
        if uid:
            bot["bot_id"] = uid
            bots.append(bot)
            gif_count = len(bot["gifs"])
            print(f"[LOAD] Token {bot['token'][:8]}... → User ID {uid} with {gif_count} GIFs")
        else:
            print(f"[LOAD] Skipping token {bot['token'][:8]}... (failed to get user_id)")

    print(f"[SYSTEM] Loaded {len(bots)} bots")
    return bots

# ================= CORE FUNCTIONS =================
async def follow_user(session, token, bot_id, target_id):
    headers = get_headers(token, bot_id)
    status, _ = await post(session, FOLLOW_USER_URL, headers, {"user_id": target_id})
    if status == 200:
        print(f"[{bot_id}] ✅ Followed target user → {target_id}")
    else:
        print(f"[{bot_id}] ❌ Failed to follow target user {target_id} – {status}")

async def active_ping(session, token, bot_id, channel):
    while True:
        await post(session, ACTIVE_PING_URL, get_headers(token, bot_id), {"channel": channel})
        print(f"[{bot_id}] 📡 Active ping")
        await asyncio.sleep(PING_DELAY)

async def become_speaker_direct(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    methods = [
        (AUDIENCE_REPLY_URL, {"channel": channel, "type": "raise_hand"}, "audience_reply"),
        (MAKE_ME_SPEAKER_URL, {"channel": channel}, "make_me_speaker"),
    ]
    for url in ACCEPT_SPEAKER_INVITE_URLS:
        methods.append((url, {"channel": channel}, f"accept_via_{url.split('/')[-1]}"))

    for url, data, method_name in methods:
        status, _ = await post(session, url, headers, data)
        if status == 200:
            print(f"[{bot_id}] ✅ Speaker request successful via {method_name}")
            return True
        else:
            print(f"[{bot_id}] ⏩ {method_name} failed (status {status})")

    print(f"[{bot_id}] ❌ All speaker request methods failed")
    return False

async def accept_speaker_invite(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    data = {"channel": channel}
    for url in ACCEPT_SPEAKER_INVITE_URLS:
        status, resp = await post(session, url, headers, data)
        if status == 200:
            print(f"[{bot_id}] ✅ Accepted speaker invite using {url}")
            return True
        else:
            print(f"[{bot_id}] ❌ Failed with {url}, status: {status}, response: {resp}")
    print(f"[{bot_id}] ❌ All accept URLs failed")
    return False

async def poll_for_speaker_invite(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    while True:
        status, data = await post(session, GET_CHANNEL_URL, headers, {"channel": channel})
        if status == 200 and data:
            for user in data.get("users", []):
                if user.get("user_id") == bot_id:
                    if not user.get("is_speaker") and user.get("is_asked_to_speak"):
                        print(f"[{bot_id}] 🎤 Speaker invite detected, accepting...")
                        await accept_speaker_invite(session, token, bot_id, channel)
                        await asyncio.sleep(10)
                    break
        await asyncio.sleep(POLL_INTERVAL)

async def leave_room(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    status, _ = await post(session, LEAVE_ROOM_URL, headers, {"channel": channel})
    if status == 200:
        print(f"[{bot_id}] 👋 Left room {channel}")
    else:
        print(f"[{bot_id}] ❌ Failed to leave room {channel}, status: {status}")

async def invite_audience_to_speaker(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    while True:
        _, data = await post(session, GET_CHANNEL_URL, headers, {"channel": channel})
        users = data.get("users", [])
        for user in users:
            if user.get("is_speaker") or user.get("user_id") == bot_id:
                continue
            uid = user.get("user_id")
            name = user.get("name", "Unknown")
            if uid:
                status, _ = await post(session, INVITE_SPEAKER_URL, headers,
                                       {"channel": channel, "user_id": uid})
                if status == 200:
                    print(f"[{bot_id}] 📨 Invited {name} ({uid}) to speak")
                else:
                    print(f"[{bot_id}] ❌ Failed to invite {name} ({uid}) – {status}")
                await asyncio.sleep(INVITE_DELAY)
        await asyncio.sleep(5)

async def auto_follow_all_users(session, token, bot_id, channel):
    headers = get_headers(token, bot_id)
    followed = set()
    while True:
        _, data = await post(session, GET_CHANNEL_URL, headers, {"channel": channel})
        users = data.get("users", [])
        print(f"[{bot_id}] 👥 Users in room: {len(users)}")
        for u in users:
            uid = u.get("user_id")
            name = u.get("name", "Unknown")
            if uid and uid != bot_id and uid not in followed:
                followed.add(uid)
                status, _ = await post(session, FOLLOW_USER_URL, headers, {"user_id": uid})
                if status == 200:
                    print(f"[{bot_id}] ✅ Followed → {name} ({uid})")
                else:
                    print(f"[{bot_id}] ❌ Follow failed → {name} ({uid}) – {status}")
                await asyncio.sleep(FOLLOW_DELAY)
        await asyncio.sleep(5)

async def send_gif(session, token, bot_id, channel, gif):
    status, _ = await post(session, GIF_REACTION_URL, get_headers(token, bot_id),
                           {"channel": channel, "giphy_id": gif})
    print(f"[{bot_id}] 🎁 GIF sent → {gif} ({status})")

async def nonstop_fast_gif(session, token, bot_id, channel, gifs):
    if not gifs:
        print(f"[{bot_id}] ⏸️ No GIFs provided – skipping GIF spam")
        return
    i = 0
    await send_gif(session, token, bot_id, channel, gifs[0])
    while True:
        await asyncio.sleep(random.uniform(GIF_MIN_DELAY, GIF_MAX_DELAY))
        i += 1
        await send_gif(session, token, bot_id, channel, gifs[i % len(gifs)])

async def get_user_id(session, token, bot_id, username):
    _, d = await post(session, USER_PROFILE_URL, get_headers(token, bot_id), {"username": username})
    uid = d.get("user_profile", {}).get("user_id")
    print(f"[{bot_id}] 🎯 Target user id → {uid}")
    return uid

async def find_user_room(session, token, bot_id, target_id):
    _, d = await post(session, FEED_URL, get_headers(token, bot_id), {})
    for i in d.get("items", []):
        ch = i.get("channel", {})
        for u in ch.get("users", []):
            if u.get("user_id") == target_id:
                return ch.get("channel")
    return None

async def track_user(bot, target_username):
    token = bot["token"]
    bot_id = bot["bot_id"]
    gifs = bot["gifs"]

    async with aiohttp.ClientSession() as session:
        target_id = await get_user_id(session, token, bot_id, target_username)
        if not target_id:
            print(f"[{bot_id}] ❌ Could not get target user ID. Exiting.")
            return

        await follow_user(session, token, bot_id, target_id)

        current_room = None
        poll_task = active_ping_task = follow_task = invite_task = gif_task = None

        while True:
            room = await find_user_room(session, token, bot_id, target_id)

            if room and room != current_room:
                if current_room:
                    print(f"[{bot_id}] 🚪 Leaving previous room: {current_room}")
                    for task in [poll_task, active_ping_task, follow_task, invite_task, gif_task]:
                        if task:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                    await leave_room(session, token, bot_id, current_room)

                print(f"[{bot_id}] 🚪 Joining new room → {room}")
                await post(session, JOIN_ROOM_URL, get_headers(token, bot_id),
                           {"channel": room, "as_speaker": True})
                await become_speaker_direct(session, token, bot_id, room)

                gif_task = asyncio.create_task(nonstop_fast_gif(session, token, bot_id, room, gifs))
                invite_task = asyncio.create_task(invite_audience_to_speaker(session, token, bot_id, room))
                active_ping_task = asyncio.create_task(active_ping(session, token, bot_id, room))
                follow_task = asyncio.create_task(auto_follow_all_users(session, token, bot_id, room))
                poll_task = asyncio.create_task(poll_for_speaker_invite(session, token, bot_id, room))
                current_room = room

            elif not room and current_room:
                print(f"[{bot_id}] 🚪 Target left room, leaving {current_room}")
                for task in [poll_task, active_ping_task, follow_task, invite_task, gif_task]:
                    if task:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                await leave_room(session, token, bot_id, current_room)
                current_room = poll_task = None

            await asyncio.sleep(5)

async def start_bot(target_username):
    bots = await load_tokens()
    if not bots:
        print("[ERROR] No valid bots loaded.")
        return
    await asyncio.gather(*[track_user(b, target_username) for b in bots])  # ← THIS WAS MISSING

async def main():
    TARGET_USERNAME = "maanbhi"
    bots = await load_tokens()
    if not bots:
        print("[ERROR] No valid bots loaded. Exiting.")
        return
    await asyncio.gather(*[track_user(b, target_username) for b in bots])

if __name__ == "__main__":
    asyncio.run(main())
