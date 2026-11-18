from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .permissions import can_dispatch


class DispatchMapConsumer(AsyncJsonWebsocketConsumer):
    group_name = "dispatch_map"

    async def connect(self):
        if not await database_sync_to_async(can_dispatch)(self.scope["user"]):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def driver_location(self, event):
        await self.send_json(event["data"])
