import asyncio

from hpxclient.mng import service as mng_service
from hpxqt import consumers as hpxqt_consumers
from hpxclient.fetcher.central import service as fetcher_central_service


async def start_manager(email, password, proxy_enabled=False):
    await asyncio.gather(
        mng_service.start_client(
            email=email,
            password=password,
            message_handler=hpxqt_consumers.process_message,
            ssl=proxy_enabled
        ),

        fetcher_central_service.start_client(
            email=email,
            password=password,
            ssl=proxy_enabled
        )
    )


def stop_manager():
    return
