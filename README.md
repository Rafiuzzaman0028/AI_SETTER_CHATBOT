# AI Setter Chatbot (JamieBot)

A conversational AI "Setter" designed specifically for Jamie's dating coaching business. The bot acts as a grounded, human-like dating coach whose primary objective is to build rapport, identify the user's core struggles, qualify them, and route them to the appropriate next step (e.g., booking a discovery call, purchasing a course, or accessing free resources).

## Core Architecture

JamieBot is built on a **Strict State Machine** architecture rather than a free-flowing autonomous agent. This ensures that the bot follows a precise sales funnel and never goes off script, while leveraging LLMs purely for natural language generation.

### Key Components:
- **State Machine (`app/state_machine/`)**: Defines the strict funnel stages (Discovery → Gap → Reframe → Qualification).
- **LLM Orchestrator (`app/orchestrator.py`)**: Connects the current conversation state to the LLM, managing prompt injection and response generation.
- **Dynamic Prompts (`app/prompts/`)**: Modular, state-specific instructions that dictate exactly what the bot should focus on and what question to ask at any given moment.
- **Intent Detection (`app/state_machine/exit_rules.py`)**: Actively listens for "buying intent" (e.g., "I'm stuck, what's next?"). If detected, the bot automatically fast-forwards through the funnel to present the Call to Action (CTA).
- **Routing Engine (`app/state_machine/transitions.py`)**: Uses collected qualification data (Location, Age, Relationship Status, Fitness, Finance) to bucket users into three distinct outcomes:
  1. **Discovery Call**: Qualified leads who meet all criteria.
  2. **Course Specific**: Unqualified leads with a specific, identified problem.
  3. **Free Guide**: Unqualified leads with vague or general problems.

## Setup & Installation

1. **Clone the repository** and navigate to the project root.
2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Mac/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables**:
   Create a `.env` file in the root directory and add your required API keys (e.g., OpenAI/Anthropic keys depending on your LLM configuration).

## Usage

### Interactive CLI Tester
The best way to test the conversation flow, prompt logic, and intent detection without starting the web server is through the CLI tester:
```bash
python interactive_chat.py
```
Type `exit` to end the chat session.

### Running the API Server
The application includes a FastAPI backend that can be used to integrate the bot into web interfaces or messaging platforms.
```bash
uvicorn app.main:app --reload
```
Once running, the API will be available at `http://localhost:8000`. You can view the API documentation by navigating to `http://localhost:8000/docs`.

## Recent Updates (Client Clarifications)
- **Early CTA Trigger**: The bot no longer forces users through the entire discovery funnel if they express an explicit desire to move forward. It detects buying intent and fast-forwards directly to qualification.
- **Smooth CTA Transition**: When transitioning to the qualification stage, the bot uses a natural, non-abrupt transition: *"The next step would be a free discovery call with Jamie. Before I send the right link, I just need to ask a few quick fit questions..."*
- **Softer Qualification Language**: The fitness qualification question has been softened to sound more consultative and less judgmental.

## Warning / Role Boundaries
The bot is strictly programmed **not** to provide actual coaching, therapy, or advice. It is a setter. If a user attempts to seek advice or go off-topic, the safety filters and orchestrator will politely redirect the conversation back to the current state.
