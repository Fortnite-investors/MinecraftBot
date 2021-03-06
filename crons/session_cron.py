import asyncio
import datetime
import pytz
from typing import Dict

import config
import postgres
import helpers
import xbox_live

from aiogram import Bot

ITERATIONS = 9
SLEEP_TIME = 60

utc = pytz.UTC


async def get_active_sessions(
        pg_client: postgres.client.PostgresClient,
) -> Dict[str, postgres.models.Session]:
    pg_sessions = await pg_client.get_active_sessions()

    sessions = {}
    for session in pg_sessions:
        sessions[session.gamertag] = session
    return sessions


async def main():
    bot = Bot(config.TOKEN)
    client = xbox_live.client.get_client()
    pg_client = await postgres.client.get_client()

    chats = await pg_client.get_subscribed_chats()

    for _ in range(ITERATIONS):
        players = await client.get_players()
        sessions = await get_active_sessions(pg_client)

        for player in players:
            if player.online and player.game.find('Minecraft') >= 0:
                if player.gamertag not in sessions:
                    await pg_client.create_new_session(player.gamertag)
                    for chat in chats:
                        await bot.send_message(int(chat.chat_id),
                                               f'{player.gamertag} is now online')
            if not player.online or player.game.find('Minecraft') == -1:
                if player.gamertag in sessions:
                    session = sessions[player.gamertag]
                    await pg_client.end_session(session.id)

                    ended_at = utc.localize(datetime.datetime.utcnow())
                    session_time = ended_at - session.start_at

                    formated_time = helpers.format_playtime(session_time)

                    for chat in chats:
                        await bot.send_message(int(chat.chat_id),
                                               f'{player.gamertag} is now '
                                               f'offline (session: {formated_time})')

        await asyncio.sleep(SLEEP_TIME)

    await client.close()
    await pg_client.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
