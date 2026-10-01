# chat/storage.py
import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator, Dict, List

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

from .models import ChatRoom, Message

User = get_user_model()

# Redis for pub/sub (production) or in-memory (development)
try:
    import aioredis
    REDIS_ENABLED = True
except ImportError:
    REDIS_ENABLED = False
    print("Redis not available, using in-memory pubsub")

class ChatStorage:
    def __init__(self):
        self._subscriptions: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._redis = None
    
    async def connect_redis(self):
        """Initialize Redis connection for production"""
        if REDIS_ENABLED:
            self._redis = await aioredis.create_redis_pool("redis://localhost")
    
    async def close(self):
        """Clean up resources"""
        if REDIS_ENABLED and self._redis:
            self._redis.close()
            await self._redis.wait_closed()
    
    @sync_to_async
    def _get_or_create_chatroom(self, name: str) -> ChatRoom:
        """Thread-safe room creation"""
        chatroom, _ = ChatRoom.objects.get_or_create(name=name)
        return chatroom
    
    @sync_to_async
    def add_message(self, chatroom_name: str, text: str, sender: User) -> Message:
        """
        Store message in database and notify subscribers
        Args:
            chatroom_name: Name of the chat room
            text: Message content
            sender: Django User instance
        Returns:
            The created Message instance
        """
        chatroom = await self._get_or_create_chatroom(chatroom_name)
        message = Message.objects.create(
            chatroom=chatroom,
            text=text,
            sender=sender
        )
        await self._publish(chatroom_name, message)
        return message
    
    @sync_to_async
    def get_messages(self, chatroom_name: str, limit: int = 100) -> List[Message]:
        """
        Retrieve message history for a chatroom
        Args:
            chatroom_name: Name of the chat room
            limit: Maximum number of messages to return
        Returns:
            List of Message instances, ordered newest first
        """
        try:
            chatroom = ChatRoom.objects.get(name=chatroom_name)
            return list(chatroom.messages.select_related('sender').order_by('-timestamp')[:limit])
        except ChatRoom.DoesNotExist:
            return []
    
    async def subscribe(self, chatroom_name: str) -> AsyncGenerator[Message, None]:
        """
        Subscribe to new messages in a chatroom
        Args:
            chatroom_name: Name of the chat room to subscribe to
        Returns:
            Async generator yielding Message instances
        """
        if REDIS_ENABLED:
            async for message in self._redis_subscribe(chatroom_name):
                yield message
        else:
            queue = asyncio.Queue()
            self._subscriptions[chatroom_name].append(queue)
            try:
                while True:
                    message = await queue.get()
                    yield message
            finally:
                # Clean up on unsubscribe
                self._subscriptions[chatroom_name].remove(queue)
    
    async def _publish(self, chatroom_name: str, message: Message):
        """
        Notify all subscribers of a new message
        Args:
            chatroom_name: Name of the chat room
            message: Message instance to publish
        """
        if REDIS_ENABLED:
            # Serialize message for Redis
            message_data = {
                'id': str(message.id),
                'chatroom': chatroom_name,
                'text': message.text,
                'sender': message.sender.username,
                'timestamp': message.timestamp.isoformat()
            }
            await self._redis.publish(chatroom_name, json.dumps(message_data))
        else:
            # In-memory notification
            for queue in self._subscriptions[chatroom_name]:
                await queue.put(message)
    
    async def _redis_subscribe(self, chatroom_name: str) -> AsyncGenerator[Message, None]:
        """
        Redis-based subscription handler
        Args:
            chatroom_name: Name of the chat room
        Returns:
            Async generator yielding Message instances
        """
        channel, = await self._redis.subscribe(chatroom_name)
        try:
            async for raw_message in channel.iter():
                message_data = json.loads(raw_message)
                yield Message(
                    id=message_data['id'],
                    chatroom=await self._get_or_create_chatroom(message_data['chatroom']),
                    text=message_data['text'],
                    sender=await sync_to_async(User.objects.get)(username=message_data['sender']),
                    timestamp=message_data['timestamp']
                )
        finally:
            await self._redis.unsubscribe(chatroom_name)