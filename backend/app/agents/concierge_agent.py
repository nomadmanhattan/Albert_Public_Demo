import logging
import uuid
import os
import json
from datetime import datetime

from app.services.cloud_logger import CloudLogger
from app.agents.agent_workflow import AlbertAgentOrchestrator
from app.services.tts_service import TextToSpeechService
from google.adk.runners import InMemoryRunner
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class ConciergeAgent:
    def __init__(self):
        try:
            self.cloud_logger = CloudLogger()
        except Exception as e:
            logger.warning(f"Failed to initialize CloudLogger: {e}. Logging will be disabled.")
            self.cloud_logger = None
        
        # Initialize Orchestrator and Agent
        self.orchestrator = AlbertAgentOrchestrator()
        root_agent = self.orchestrator.create_agent()

        # Wrap with App and Context Caching
        self.app = App(
            name="albert-concierge",
            root_agent=root_agent,
            context_cache_config=ContextCacheConfig(
                min_tokens=2000,
                ttl_seconds=3600,
                cache_intervals=3
            )
        )

        self.runner = InMemoryRunner(agent=self.app)
        
        # Initialize TTS Service
        try:
            self.tts_service = TextToSpeechService()
        except Exception as e:
            logger.error(f"Failed to initialize TTS Service: {e}")
            self.tts_service = None

    async def process_request(self, user_input: str) -> dict:
        """
        Processes user input using the ADK pipeline with Smart Logging.
        """
        session_id = str(uuid.uuid4())
        model_name = self.orchestrator.model_name
        logger.info(f"Processing request '{user_input}' with model '{model_name}' (Session: {session_id})")

        response_text = ""
        action_taken = "adk_pipeline"
        final_state = {}
        
        with tracer.start_as_current_span("process_request") as span:
            span.set_attribute("session_id", session_id)
            span.set_attribute("user_id", "user")
            span.set_attribute("model", model_name)
            span.set_attribute("input", user_input)

            try:
                # Ensure session exists with initial state
                app_name = getattr(self.runner, "app_name", "albert-concierge")
                await self.runner.session_service.create_session(
                    session_id=session_id, 
                    user_id="user", 
                    app_name=app_name,
                    state={
                        "current_digest": "",
                        "critique": "",
                        "verbose_logging": False # Default to minimal logging
                    }
                )

                # Construct Message
                class SimplePart:
                    def __init__(self, text):
                        self.text = text
                class SimpleMessage:
                    def __init__(self, role, content):
                        self.role = role
                        self.parts = [SimplePart(content)]

                user_msg = SimpleMessage(role="user", content=user_input)

                # Run Pipeline Async
                async for event in self.runner.run_async(
                    user_id="user",
                    session_id=session_id,
                    new_message=user_msg
                ):
                    # Trace and Log Intermediate Steps
                    if hasattr(event, "text") and event.text:
                        response_text = event.text
                        # NOTE to self : to revisit after implementing smart logging to decide if intermediate logs is still needed.
                        # For now, keep them debug level or minimal
                    
                    if hasattr(event, "tool_calls") and event.tool_calls:
                        logger.info(f"Tool called: {event.tool_calls}")

                    # Capture final state if available (simplified check)
                    if hasattr(event, "actions") and event.actions and hasattr(event.actions, "state_delta"):
                         final_state.update(event.actions.state_delta)
                
                # Fetch final state to check output keys
                session = await self.runner.session_service.get_session(
                    session_id=session_id,
                    user_id="user",
                    app_name=app_name
                )
                if session and session.events:
                     # Attempt to find text if not captured
                     if not response_text:
                         for event in reversed(session.events):
                              if hasattr(event, "content") and event.content:
                                   if isinstance(event.content, str):
                                       response_text = event.content
                                       break
                                   elif hasattr(event.content, "parts"):
                                       parts_text = "".join([p.text for p in event.content.parts if hasattr(p, "text")])
                                       if parts_text:
                                           response_text = parts_text
                                           break

                # Deterministic Audio Generation
                if response_text and self.tts_service:
                    try:
                        logger.info("Generating audio for digest...")
                        import asyncio
                        with tracer.start_as_current_span("generate_audio"):
                            audio_url = await asyncio.to_thread(self.tts_service.generate_audio, response_text)
                            logger.info(f"Audio generated successfully: {audio_url}")
                            
                            user_input_lower = user_input.lower()
                            wants_text = any(keyword in user_input_lower for keyword in ["text", "read", "summary", "bullet", "show me", "written"])
                            
                            audio_message = f"\n\n🎧 **[Listen to your Audio Digest Now! (opening in a new browser)]({audio_url})**"
                            
                            if wants_text:
                                response_text += audio_message
                            else:
                                response_text = f"I've cooked up a fresh audio digest for you! {audio_message} Please note that the audio digest will be available for 48 hours. \n So don't leave me hanging for too long 😉."

                    except Exception as e:
                        logger.error(f"Failed to generate audio: {e}")
                        response_text += f"\n(Audio generation failed: {str(e)})"

            except Exception as e:
                logger.error(f"Error in ADK interaction: {e}")
                response_text = f"I encountered an error: {str(e)}"
                span.record_exception(e)
                action_taken = "error"
                
                if self.cloud_logger:
                    self.cloud_logger.log_struct({
                        "session_id": session_id,
                        "status": 500,
                        "error": str(e),
                        "action": "error_log"
                    })

            # --- SMART LOGGING ---
            # Inspect state or output keys to decide verbosity
             
            is_verbose = final_state.get("verbose_logging", False)
            if self.cloud_logger:
                if is_verbose or action_taken == "error":
                     self.cloud_logger.log_struct({
                        "session_id": session_id,
                        "user_input": user_input,
                        "response": response_text[:5000],
                        "action": action_taken,
                        "model": model_name,
                        "status": 200 if action_taken != "error" else 500,
                        "log_type": "full"
                    })
                else:
                    # Minimal Log
                    self.cloud_logger.log_struct({
                        "session_id": session_id,
                        "status": 200,
                        "action": action_taken,
                        "log_type": "minimal",
                        "response_length": len(response_text)
                    })

            return {
                "response": response_text,
                "session_id": session_id,
                "model": model_name
            }
