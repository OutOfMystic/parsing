import asyncio
import platform
import threading
import time
from asyncio import AbstractEventLoop
from typing import Optional

from .pooling import ScheduledExecutor
from .parser import AsyncEventParser, AsyncSeatsParser


def create_thread_with_event_loop() -> AbstractEventLoop:
    loop: Optional[AbstractEventLoop] = None

    def thread_target():
        nonlocal loop
        #if platform.system() == 'Windows':
        #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        #loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=thread_target)
    thread.start()

    start_time = time.time()
    while loop is None:
        if time.time() - start_time > 10:
            raise RuntimeError('Event loop initialization timeout')
        time.sleep(0.01)

    return loop
