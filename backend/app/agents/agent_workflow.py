
import os
import logging
from typing import Dict, Any
from google.adk.agents import LoopAgent, LlmAgent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from app.agents.email_aggregator import EmailAggregator
from app.services.user_context_service import UserContextService

logger = logging.getLogger(__name__)

# --- Tools ---

def exit_loop(tool_context: ToolContext):
    """
    Call this function ONLY when the critic approves the digest or max iteractions are met, signaling the refinement loop should end.
    """
    logger.info(f" [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    tool_context.actions.escalate = True
    return {}



# --- Agents Orchestration ---

class AlbertAgentOrchestrator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.email_aggregator = EmailAggregator()
        self.context_service = UserContextService()

    def create_agent(self) -> SequentialAgent:
        # 1. Email Aggregator Agent
        # Task: Search relevant emails based on semantic similarity between user's query and email labels (if exists),
        # or email subjects lines. Return top 20 emails matched.
        
        def fetch_emails_tool(tool_context: ToolContext, query: str, days: int = 14) -> str:
            """
            Fetches and ranks emails based on the semantic similarity with the user query.
            Args:
                tool_context: The tool context.
                query: The user's intent/topic (e.g., "AI news", "Project updates").
                days: Number of days to look back (default 14).
            """
            # Persist query as a label proxy for now
            self.context_service.set_last_labels([query])
            
            # Initialize loop variables if missing
            # Access state directly from tool_context
            if "current_digest" not in tool_context.state:
                tool_context.state["current_digest"] = ""
            if "critique" not in tool_context.state:
                tool_context.state["critique"] = ""
            
            # Use semantic search
            logger.info(f" [Tool Call] fetch_emails_tool executing for query: {query}")
            emails = self.email_aggregator.semantic_search(query, days=days, max_results=50)
            logger.info(f" [Tool Call] fetch_emails_tool returned {len(emails)} emails")
            return str(emails)

        aggregator_agent = LlmAgent(
            name="EmailAggregator",
            model=self.model_name,
            instruction="""
            You are an Email Assistant. Your goal is to fetch emails based on the user's request.
            1. Understand the user's intent (e.g., "AI news", "Job market trends").
            2. Extract the time range if specified (e.g., "last 3 days" -> days=3). If not specified, default to 14 days.
            3. Call the 'fetch_emails_tool' with the intent as the query and the extracted number of days.
            4. Output the retrieved emails into the context for the next agent.
            """,
            tools=[fetch_emails_tool],
            output_key="emails_content" 
        )

        # 2. Refinement Loop
        # Task: Generate and refine the draft based on the user's feedback.
        
        # 2a. Drafter
        drafter_agent = LlmAgent(
            name="Drafter",
            model=self.model_name,
            instruction="""
            You are an expert news editor. 
            Input Emails: {{emails_content}}
            Current Draft: {{current_digest}}
            Critique: {{critique}}
            
            Task:
            If 'Current Draft' is empty, write a concise, engaging news digest based on 'Input Emails'.
            If 'Critique' is present, refine the 'Current Draft' based on the feedback.
            
            Style Requirements:
            - Mimic the tone of NYT Hardfork (https://podscan.fm/podcasts/the-daily/episodes/hard-fork-an-interview-with-sam-altman) or Peter Kafka https://podcasts.voxmedia.com/show/channels-with-peter-kafka.
            - Be conversational, insightful, and slightly witty.
            - Focus on the "so what?" - why does this news matter?
            
            Output ONLY the digest text.
            """,
            output_key="current_digest"
        )

        # 2b. Critic
        critic_agent = LlmAgent(
            name="Critic",
            model=self.model_name,
            instruction="""
            You are a Senior Editor at New Yorker Magazine.
            Draft to Review: {{current_digest}}
            
            Task:
            Review the draft against the following criteria:
            1. **Style**: Does it sound like NYT Hardfork / Peter Kafka? Is it conversational and witty?
            2. **Substance**: Does it capture the key points from the emails?
            3. **Conciseness**: Is it referencing data points without being verbose?
            
            If the draft meets these criteria, call the 'exit_loop' tool.
            If it needs improvement (especially on tone/style), provide specific, actionable feedback.
            """,
            tools=[exit_loop],
            output_key="critique"
        )

        refinement_loop = LoopAgent(
            name="RefinementLoop",
            sub_agents=[drafter_agent, critic_agent],
            max_iterations=3
        )



        # Create Sequential Agent
        # The SequentialAgent will run these agents in order.
        # 1. Aggregator: Fetches emails.
        # 2. RefinementLoop: Drafts and critiques the digest.
        # 3. AudioGenerator: Converts the final digest to audio.
        
        sequential_agent = SequentialAgent(
            name="AlbertOrchestrator",
            sub_agents=[aggregator_agent, refinement_loop]
        )
        
        return sequential_agent
