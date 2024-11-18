import asyncio
import random
import ssl
import json
import time
import uuid
import requests
import shutil
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
import base64

user_agent = UserAgent(os='windows', platforms='pc', browsers='chrome')
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "4.26.2",
                                "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)

async def refresh_proxies():
    while True:
        # Wait for 5 minutes (300 seconds)
        await asyncio.sleep(300)
        logger.info("Refreshing proxies...")
        
        # Reload proxies from the file
        with open('proxies.txt', 'r') as proxy_file:
            proxies = proxy_file.read().splitlines()

        logger.info(f"Loaded {len(proxies)} proxies")

        # Now restart the WebSocket connections with the new proxies
        await initiate_connections(proxies)

async def initiate_connections(proxies):
    # Read user IDs
    with open('user_id.txt', 'r') as user_file:
        user_ids = user_file.read().splitlines()
    
    logger.info(f"Jumlah akun: {len(user_ids)}")
    
    tasks = []
    proxy_count = len(proxies)
    user_count = len(user_ids)
    
    # Ensure that every proxy is used at least once and each user_id gets a proxy
    for i in range(max(proxy_count, user_count)):
        user_id = user_ids[i % user_count]  # Cycle through user_ids if there are more proxies than user_ids
        proxy = proxies[i % proxy_count]    # Cycle through proxies if there are more user_ids than proxies
        tasks.append(asyncio.ensure_future(connect_to_wss(proxy, user_id)))
    
    # Execute the tasks
    await asyncio.gather(*tasks)

async def main():
    # Initial load of proxies and user IDs
    with open('proxies.txt', 'r') as proxy_file:
        proxies = proxy_file.read().splitlines()
    
    # Load user IDs
    with open('user_id.txt', 'r') as user_file:
        user_ids = user_file.read().splitlines()
    
    logger.info(f"Jumlah akun: {len(user_ids)}")
    
    # Start the initial WebSocket connection
    await initiate_connections(proxies)
    
    # Start the task to refresh proxies every 5 minutes
    await refresh_proxies()

if __name__ == '__main__':
    asyncio.run(main())