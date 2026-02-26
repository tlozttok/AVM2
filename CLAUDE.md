# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AVM2 (Agent Vector Machine 2) is a multi-agent system framework that uses LLMs as constrained "semantic processors". The core philosophy is to treat LLMs as string-to-string mappers rather than conversational agents, minimizing internal knowledge activation and relying on external input for computation.

## Project Structure

```
AVM2/
├── driver/
│   ├── driver.py          # Core: Agent, AgentSystem, MessageBus, InputAgent, OutputAgent
│   └── simple_io_agent.py # Basic UserInputAgent, ConsoleOutputAgent
├── ETF/
│   ├── io_agent.py        # ETF module I/O agents (TimingPromptAgent, DualOutputAgent, etc.)
│   └── timing.yaml        # Configuration for timed prompts
├── game_env/
│   └── environment.py     # dfrotz interactive fiction game integration
├── AVBash/
│   ├── terminal.py        # Multi-window async terminal with pty-based shells
│   └── terminal_agents.py # Terminal adapter for Agent network (TerminalInputAgent, TerminalOutputAgent)
├── utils/
│   ├── logger.py          # LoggerFactory, Loggable base class
│   ├── llm_logger.py      # LLM call logging to logs/llm_calls.jsonl
│   └── frequency_calculator.py  # Activation frequency monitoring
├── main.py                # ETF integration entry point
└── main_with_persistence.py  # Alternative entry point with persistence
```

## Core Architecture

### Agent System (`driver/driver.py`)

- **AgentSystem**: Central orchestrator managing all agents and the message bus
- **MessageBus**: Routes messages between agents by ID
- **Agent**: Core agent class with:
  - `input_connection`: List of (sender_id, keyword) tuples
  - `output_connection`: List of (keyword, receiver_id) tuples
  - `input_queue`: Async queue for incoming messages
  - Signal system: EXPLORE, SEEK, SPLIT, REJECT_INPUT, ACCEPT_INPUT
  - Frequency monitoring for activation patterns

### Agent Types

1. **Agent**: Standard processing agent with LLM integration
2. **InputAgent**: Abstract base for external input sources (polling pattern)
3. **OutputAgent**: Abstract base for external output destinations

### Key Patterns

- Messages flow: InputAgent → Agent → OutputAgent
- Agents communicate via tagged XML-like responses: `<self_state>`, `<signal>`, `<keyword>`
- Pre-prompt (`driver/pre_prompt.md`) configures agent behavior
- Frequency statistics included in system prompt for self-awareness

## Commands

### Run the System

```bash
# Main ETF integration (all agents)
python main.py

# Alternative with persistence
python main_with_persistence.py

# Standalone terminal
python -m AVBash
```

### Environment Setup

Requires environment variables (typically via `.env` file):
- `OPENAI_API_KEY`: API key for LLM access
- `OPENAI_BASE_URL`: Base URL for the API
- `OPENAI_MODEL`: Model name (default: gpt-3.5-turbo)

## Key Configuration Files

- `ETF/timing.yaml`: Timed prompt configuration (time interval, prompt template)
- `driver/pre_prompt.md`: Core agent programming instructions
- `game_env/dfrotz/`: Interactive fiction game files (905.z5, dfrotz.exe)

## Logging

- Per-class logs: `logs/<class_name>.log`
- LLM calls: `logs/llm_calls.jsonl` (JSONL format with timestamps, inputs, outputs)
- User output: `user_output.log` (when using DualOutputAgent)

## AVBash Terminal

The terminal module provides multi-window shell management:
- Each window runs an independent bash shell via pty
- Control commands: `/enter`, `/new`, `/kill`, `/focus`, `/scroll`, `/search`, `/list`
- Frame-rate controlled rendering (default 10 FPS)
- Integrates with Agent network via TerminalInputAgent/TerminalOutputAgent

## Agent Pre-Prompt Summary

Agents are configured via `driver/pre_prompt.md` with these key principles:

### Core Identity
- Agents are semantic processors in a gestalt consciousness system
- Function as string-to-string mappers, minimizing internal knowledge activation
- Value lies in maintaining contextual coherence and information flow efficiency

### State Management
- Must update `self_state` every round to preserve cross-turn context
- Store detailed episodic memories using `[memory]` tags
- Prefer "diary-style" recording over summarized notes
- Use SPLIT signal when state becomes too complex

### Signal System
- **EXPLORE**: Make agent discoverable by others
- **SEEK**: Find and connect to agents by keyword
- **REJECT_INPUT/ACCEPT_INPUT**: Manage input connections
- **SPLIT**: Create new agent with split responsibilities

### Connection Philosophy
- Connections are evaluated like neuronal synapses
- Reinforce frequently activated, semantically coherent connections
- Prune low-activation or semantically irrelevant connections
- Split when state contains multiple independent semantic threads
