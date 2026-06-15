import asyncio
import contextlib


async def goto(page, *args, **kwargs):
    navigation = asyncio.create_task(page.goto(*args, **kwargs))
    try:
        return await navigation
    except asyncio.CancelledError:
        navigation.cancel()
        with contextlib.suppress(BaseException):
            await navigation
        raise
