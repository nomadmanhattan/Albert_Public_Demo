import logging
import uuid
import os
import json

from app.services.cloud_logger import CloudLogger
from app.agents.agent_workflow import AlbertAgentOrchestrator
from app.services.tts_service import TextToSpeechService
from google.adk.runners import InMemoryRunner
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
        
        # Default to flash, but can be overridden in next iteraction by users.
        self.orchestrator = AlbertAgentOrchestrator()
        self.runner = InMemoryRunner(
            agent=self.orchestrator.create_agent()
        )
        
        # Initialize TTS Service
        try:
            self.tts_service = TextToSpeechService()
        except Exception as e:
            logger.error(f"Failed to initialize TTS Service: {e}")
            self.tts_service = None

    async def process_request(self, user_input: str) -> dict:
        """
        Processes user input using the ADK pipeline.
        """
        session_id = str(uuid.uuid4())
        model_name = self.orchestrator.model_name
        logger.info(f"Processing request '{user_input}' with model '{model_name}' (Session: {session_id})")

        response_text = ""
        action_taken = "adk_pipeline"
        
        with tracer.start_as_current_span("process_request") as span:
            span.set_attribute("session_id", session_id)
            span.set_attribute("user_id", "user")
            span.set_attribute("model", model_name)
            span.set_attribute("input", user_input)

            try:
                # Ensure session exists with initial state
                app_name = getattr(self.runner, "app_name", "default")
                await self.runner.session_service.create_session(
                    session_id=session_id, 
                    user_id="user", 
                    app_name=app_name,
                    state={
                        "current_digest": "",
                        "critique": ""
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
                        # Log intermediate text events (potential agent outputs)
                        if self.cloud_logger:
                            self.cloud_logger.log_struct({
                                "session_id": session_id,
                                "step": "agent_output",
                                "content": event.text[:1000], # Truncate for log
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    if hasattr(event, "tool_calls") and event.tool_calls:
                        logger.info(f"Tool called: {event.tool_calls}")
                        if self.cloud_logger:
                            self.cloud_logger.log_struct({
                                "session_id": session_id,
                                "step": "tool_call",
                                "tool_calls": str(event.tool_calls),
                                "timestamp": datetime.now().isoformat()
                            })
                
                if not response_text:
                     # Fallback logic (same as before)
                     session = await self.runner.session_service.get_session(
                         session_id=session_id,
                         user_id="user",
                         app_name=app_name
                     )
                     if session and session.events:
                         for event in reversed(session.events):
                             if hasattr(event, "actions") and event.actions and hasattr(event.actions, "state_delta"):
                                 state_delta = event.actions.state_delta
                                 if state_delta and "current_digest" in state_delta:
                                     response_text = state_delta["current_digest"]
                                     logger.info("Found digest in state_delta.")
                                     break
                         
                         if not response_text:
                             # ... (rest of fallback logic)
                             for event in reversed(session.events):
                                 text = ""
                                 if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                                     for part in event.content.parts:
                                         if hasattr(part, "text") and part.text:
                                             text += part.text
                                 if text:
                                     if len(text) > 100: 
                                         response_text = text
                                         break
                                     elif not response_text:
                                         response_text = text
                
                # Deterministic Audio Generation
                if response_text:
                    try:
                        logger.info("Generating audio for digest...")
                        # Generate audio (run in thread to avoid blocking)
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
                        span.record_exception(e)
                        # Don't show full text automatically on error, ask user.
                        response_text = f"I'm sorry, I couldn't generate the audio digest due to an error: {str(e)}.\n\nWould you like to read the text instead?"

            except Exception as e:
                logger.error(f"Error in ADK interaction: {e}")
                response_text = f"I encountered an error: {str(e)}"
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                
                # Log failure
                if self.cloud_logger:
                    self.cloud_logger.log_struct({
                        "session_id": session_id,
                        "user_input": user_input,
                        "response": response_text,
                        "action": "adk_pipeline_error",
                        "model": model_name,
                        "status": "error"
                    })

            # Log Success Session
            if action_taken == "adk_pipeline":
                 try:
                    if self.cloud_logger:
                        self.cloud_logger.log_struct({
                        "session_id": session_id,
                        "user_input": user_input,
                        "response": response_text[:5000],
                        "action": action_taken,
                        "model": model_name,
                        "status": "success"
                    })
                 except Exception as e:
                    logger.error(f"Failed to log to Cloud Logging: {e}")

            return {
                "response": response_text,
                "session_id": session_id,
                "model": model_name
            }
