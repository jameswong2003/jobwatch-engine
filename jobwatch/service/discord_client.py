import discord
from typing import List
from jobwatch.models.Job import Job

class DiscordClient(discord.Client):
    def __init__(self, notification_channel_id: int, **options):
        super().__init__(**options)
        self.notification_channel_id = notification_channel_id

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def publish_jobs(self, jobs: List[Job]):
        channel = self.get_channel(self.notification_channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            print(f"Channel with ID {self.notification_channel_id} not found or cannot receive messages.")
            return
        
        for job in jobs:
            await channel.send(f"📢 New Job: **{job.job_title}** at {job.company.company_name}\n{job.job_posting_url}")
