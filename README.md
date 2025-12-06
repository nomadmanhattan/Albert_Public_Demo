# Albert - Your Personal News Concierge 🎙️🤖

**Turn your email newsletters into a daily podcast!**

Albert is a friendly AI assistant that lives in your browser. He reads your inbox, understands your intent (e.g., "AI news", "Project updates"), and uses **Vertex AI Text-to-Speech** to turn it into an engaging audio podcast.

Powered by **Google Agent Development Kit (ADK)** and **Gemini 2.5 Flash**, Albert uses a sophisticated multi-agent loop to ensure your digest is high-quality, witty, and concise.



## Features

-   **Semantic Search**: Just say "What's happening in AI?" or "Summarize my project updates". Albert uses **Gemini Embeddings** to find relevant emails even without explicit labels.
-   **Editorial Quality**: A dedicated **Refinement Loop** (Draft -> Critique -> Refine) ensures the digest sounds like a professional podcast (think *NYT Hardfork* style).
-   **Smart Memory**: Albert remembers your last query. Just say "Run it again" to get your usual fix.
-   **Audio Magic**: Automatically uses Vertex AI Text-to-Speech to generate realistic, conversational audio mimic NYT Hardfork podcast style.
-   **Fun Interface**: A playful, KAWS-inspired design that makes news less boring.


## Architecture
Albert is a personal concierge assistant built on top of **Google Agent Development Kit (ADK)** framework, employing a multi-agent loop powered by **Gemini 2.5 Flash** and **Vertex AI Text-to-Speech** services to deliver high-quality, witty, and concise daily digests for users on the go.

1. **Concierge Agent (Orchestrator)**:
        *   Manages the user session and coordinates the workflow.
        *   **Deterministic Handoff**: Once the content is ready, the Concierge *directly* calls the TTS service, ensuring 100% reliability.

2. **Content Generation Pipeline (Google ADK)**:
        *   **Email Aggregator**: Fetches up to 50 emails based on user intent and semantic search.
        *   **Refinement Loop (LoopAgent)**:
            *   **Drafter**: Synthesizes the initial digest in the style of a news editor.
            *   **Critic**: Reviews the digest for quality, tone, and conciseness.
            *   *Loop continues until the Critic approves or max iterations reached.*

3. **Audio Generation (Service Layer)**:
        *   **Goal**: Convert the finalized text digest into an audio format ("podcast").
        *   **Tool**: **Google Cloud Vertex AI Text-to-Speech**.
        *   **Process**:
            1.  The Concierge receives the approved text from the ADK pipeline.
            2.  It calls the `TextToSpeechService` directly.
            3.  The audio file is saved locally and a playback link is returned to the user.


~~~
flowchart TD
  subgraph Client["Client"]
    U[User]
    FE[React + Vite + Tailwind (Albert UI)]
  end

  U --> FE

  subgraph Backend["Backend (FastAPI + Docker)"]
    CONC[Concierge Agent (Orchestrator)]
    subgraph ADK["Google Agent Development Kit (ADK) Pipeline"]
      EA[Email Aggregator (Gmail + Semantic Filter)]
      subgraph Loop["Refinement Loop (LoopAgent)"]
        D[Drafter (Initial Digest)]
        C[Critic (Review & Refine)]
      end
    end
    TTS_SVC[TextToSpeechService Wrapper]
  end

  FE -->|REST / WebSocket| CONC

  subgraph GoogleCloud["Google Cloud"]
    subgraph GmailAPI["Gmail API"]
      GM[Gmail Inbox]
    end

    subgraph VertexAI["Vertex AI"]
      LLM[Gemini 2.5 Flash (Synthesis)]
      TTS[Vertex AI Text-to-Speech]
    end

    subgraph Storage["Storage & Infra"]
      GCS[Google Cloud Storage (Audio Files)]
      LOG[Cloud Logging]
      TRACE[Cloud Trace]
    end
  end

  CONC --> ADK

  EA --> GM
  GM --> EA

  EA --> D
  D --> C
  C --> D
  C --> CONC

  D --> LLM
  C --> LLM
  LLM --> D
  LLM --> C

  CONC --> TTS_SVC
  TTS_SVC --> TTS
  TTS --> GCS
  GCS --> CONC
  CONC --> FE

  CONC --> LOG
  EA --> LOG
  D --> LOG
  C --> LOG
  TTS_SVC --> LOG

  CONC --> TRACE

~~~











   

## Getting Started

### Prerequisites
-   **Python 3.9+**
-   **Node.js & npm**
-   **Google Account** (for Gmail)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/nomadmanhattan/Personal_News_Digest_Assistant.git
    cd Personal_News_Digest_Assistant
    ```

2.  **Backend Setup**:
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    playwright install chromium
    ```

3.  **Frontend Setup**:
    ```bash
    cd ../frontend
    npm install
    ```

4.  **Environment Variables**:
    Create a `.env` file in `backend/` with your Google Cloud credentials (if using GCS) or Gemini API key.
    ```env
    GOOGLE_API_KEY=your_api_key_here
    ```

### Running with Docker (Recommended)

> **Important**: For the first run, you must run the backend **locally** (see below) to sign in to Google. This creates a session file that Docker will use.

1.  **Run Locally Once**: Follow "Running Locally" steps to sign in.
2.  **Start with Docker**:
    ```bash
    docker-compose up --build
    ```
3.  **Open your browser** to `http://localhost:3000`.

### Running Locally (Manual)

1.  **Start the Backend**:
    ```bash
    # In backend/ directory
    source venv/bin/activate
    uvicorn main:app --reload
    ```

2.  **Start the Frontend**:
    ```bash
    # In frontend/ directory
    npm run dev
    ```

3.  **Open your browser** to `http://localhost:5173`.

### How to Use

1.  **Say Hello**: Tell Albert what you want, e.g., "Make me a podcast about AI updates in the last 3 days".
2.  **First Run**: Albert will ask you to log in to Gmail if you haven't already.
3.  **Listen**: Wait a moment, and Albert will give you a link to your generated audio overview!

## Observability & Evaluation

Albert is designed with enterprise-grade observability to help you debug agent behavior and optimize performance.

### 1. Google Cloud Trace
Visualize the full latency breakdown of your agent pipeline.
-   **Trace Spans**: See exactly how long each step takes (e.g., `process_request`, `generate_audio`, `adk_pipeline`).
-   **Attributes**: Each trace includes metadata like `session_id`, `model`, and `user_input`.

### 2. Google Cloud Logging
Structured logs for deep debugging.
-   **Agent Thoughts**: View the raw output from the `Drafter` and `Critic` agents.
-   **Tool Calls**: See exactly which tools were called and with what arguments.
-   **Errors**: Stack traces and error messages are captured with full context.

### 3. Session Logs (Local)
JSON logs are also saved locally in `backend/logs/sessions/` for quick debugging without cloud access.

### Configuration
Update your `.env` file:
```env
GOOGLE_API_KEY=your_api_key
ENABLE_CLOUD_TRACE=true
GOOGLE_APPLICATION_CREDENTIALS=certs/albert-logger-GCP-key.json
```

## 📄 License
MIT
