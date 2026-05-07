from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.routes import health, chat
from app.db.session import session_scope
from app.db.repository import ConversationRepository
from app.llm.litellm_client import LiteLLMClient
from app.retrieval.chroma_client import ChromaIndex, ChromaRetriever
from app.tools import build_default_registry
from app.orchestrator import ChatOrchestrator


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Support Bot")
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(health.router)
    app.include_router(chat.router)
    return app


def build_orchestrator() -> ChatOrchestrator:
    settings = get_settings()
    llm = LiteLLMClient(
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_api_key,
        chat_model=settings.litellm_chat_model,
        embedding_model=settings.litellm_embedding_model,
    )
    index = ChromaIndex(persist_dir=f"{settings.data_dir}/chroma")
    retriever = ChromaRetriever(index, llm)
    tools = build_default_registry(settings)

    class _ScopedRepo:
        def __getattr__(self, name):
            def call(*a, **kw):
                with session_scope() as s:
                    return getattr(ConversationRepository(s), name)(*a, **kw)
            return call

    return ChatOrchestrator(repo=_ScopedRepo(), llm=llm, retriever=retriever, tools=tools)


app = create_app()
