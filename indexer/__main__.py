import asyncio
import logging
from datetime import datetime, UTC
from pathlib import Path
from app.config import get_settings
from app.llm.litellm_client import LiteLLMClient
from app.retrieval.chroma_client import ChromaIndex
from indexer.git_source import GitSource
from indexer.runner import IndexRun
from indexer.watermark import WatermarkStore

log = logging.getLogger("indexer")


async def _run_once():
    settings = get_settings()
    data = Path(settings.data_dir)
    git_src = GitSource(repo_url=settings.github_repo_url, workdir=data / "repo", token=settings.github_token)
    llm = LiteLLMClient(
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_api_key,
        chat_model=settings.litellm_chat_model,
        embedding_model=settings.litellm_embedding_model,
    )
    chroma = ChromaIndex(persist_dir=str(data / "chroma"))
    wm = WatermarkStore(data / "watermarks.json")
    run = IndexRun(git_source=git_src, llm=llm, index=chroma, watermarks=wm)
    summary = await run.execute()
    log.info("indexer run complete", extra={"summary": summary.__dict__})


async def main():
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    interval = max(1, settings.indexer_interval_hours) * 3600
    while True:
        try:
            await _run_once()
        except Exception:
            log.exception("indexer run failed")
        log.info("sleeping %ss until next run", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
