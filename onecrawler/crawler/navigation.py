import asyncio
import contextlib


async def goto(page, *args, settle_delay: int = 0, **kwargs):
    navigation = asyncio.create_task(page.goto(*args, **kwargs))
    try:
        response = await navigation
    except asyncio.CancelledError:
        navigation.cancel()
        with contextlib.suppress(BaseException):
            await navigation
        raise

    # Give client-side/JS-rendered content time to hydrate before the caller
    # captures the page. Best-effort: never fail navigation over the wait.
    if settle_delay and settle_delay > 0:
        with contextlib.suppress(Exception):
            await page.wait_for_timeout(settle_delay)

    return response
