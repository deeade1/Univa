# test_websocket.py
import asyncio
import websockets
import json
import sys

async def test_connection():
    uri = "ws://localhost:8000/graphql/"
    
    try:
        print("🔄 Attempting WebSocket connection...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Send connection init
            connection_init = {
                "type": "connection_init",
                "payload": {
                    "headers": {
                        "authorization": "Bearer YOUR_TEST_TOKEN_HERE"  # Replace with actual token
                    }
                }
            }
            
            print(f"📤 Sending: {connection_init}")
            await websocket.send(json.dumps(connection_init))
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Send subscription
            subscription_msg = {
                "id": "1",
                "type": "start",
                "payload": {
                    "query": """
                        subscription OnNewMessage($chatroomIds: [ID!]) {
                            onNewMessage(chatroomIds: $chatroomIds) {
                                message {
                                    id
                                    text
                                }
                                chatroomId
                            }
                        }
                    """,
                    "variables": {
                        "chatroomIds": ["test-chatroom-id"]
                    }
                }
            }
            
            print(f"📤 Sending subscription: {subscription_msg}")
            await websocket.send(json.dumps(subscription_msg))
            
            # Keep listening for messages
            async for message in websocket:
                print(f"📥 Message: {message}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())