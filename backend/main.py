from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)

# OpenTelemetry Setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

if os.getenv("ENABLE_CLOUD_TRACE", "false").lower() == "true":
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "albert-concierge")
    })
    tracer_provider = TracerProvider(resource=resource)
    # Use Google Cloud Trace Exporter
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(cloud_trace_exporter)
    )
    trace.set_tracer_provider(tracer_provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(title="Personal News Digest Assistant API", lifespan=lifespan)

if os.getenv("ENABLE_CLOUD_TRACE", "false").lower() == "true":
    FastAPIInstrumentor.instrument_app(app)

from fastapi.staticfiles import StaticFiles

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Personal News Digest Assistant API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

from fastapi.responses import FileResponse

@app.get("/download/{filename}")
async def download_audio(filename: str):
    file_path = os.path.join("static", "audio", filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename=filename, 
            media_type='audio/mpeg', 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    return {"error": "File not found"}

from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        from app.agents.concierge_agent import ConciergeAgent
        print("Initializing ConciergeAgent...")
        agent = ConciergeAgent()
        print("Processing request...")
        response = await agent.process_request(request.message)
        return response
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in /chat: {e}")
        traceback.print_exc()
        return {"response": f"Backend Error: {str(e)}", "session_id": "error", "model": "error"}
