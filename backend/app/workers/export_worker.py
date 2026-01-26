import asyncio


async def run_worker() -> None:
    """Background worker để xử lý export jobs (PPTX/Excel)."""
    while True:
        # TODO: Poll DB cho pending export jobs
        # TODO: Xử lý job với ProcessPool
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_worker())
