# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AVM2 (Agent Vector Machine 2) is a multi-agent system framework that uses LLMs as constrained "semantic processors". The core philosophy is to treat LLMs as string-to-string mappers rather than conversational agents, minimizing internal knowledge activation and relying on external input for computation.

## Project Structure

```
AVM2/
├── driver/
│   ├── agent.py              # Core Agent class (LLM-based semantic processor)
│   ├── agent_system.py       # AgentSystem and MessageBus (orchestration)
│   ├── i_o_agent.py          # InputAgent and OutputAgent abstract base classes
│   ├── net.py                # AgentNetwork (topology management)
│   ├── simple_io_agent.py    # Basic UserInputAgent, ConsoleOutputAgent
│   └── pre_prompt.md         # Core agent programming instructions
├── AVBash/
│   ├── terminal.py           # Multi-window async terminal with pty-based shells
│   └── terminal_agents.py    # Terminal I/O Agent adapters (TerminalPair)
├── utils/
│   ├── visual_monitor/       # Web-based visualization dashboard
│   │   ├── server.py         # FastAPI/WebSocket server for real-time monitoring
│   │   ├── log_monitor.py    # Log file watcher and parser
│   │   ├── unified_logger.py # JSONL logging system (Loggable base class)
│   │   ├── templates/        # HTML templates
│   │   └── static/           # CSS/JS assets
│   ├── persistence/          # Checkpoint and state persistence
│   │   ├── checkpoint_manager.py
│   │   └── utils.py
│   ├── logger.py             # Legacy LoggerFactory
│   ├── llm_logger.py         # LLM call logging
│   ├── agent_message_logger.py  # Agent message logging
│   ├── detail_logger.py      # Detailed execution logging
│   ├── async_monitor.py      # Async task monitoring
│   ├── frequency_calculator.py  # Activation frequency tracking
│   └── generate_class_config.py # Config generation utility
├── main.py                   # Main entry point
├── run_demo.py               # Demo runner
└── test_*.py                 # Test scripts

```

## Core Architecture

### Agent System

The system consists of three main components:

#### 1. Agent (`driver/agent.py`)

Core processing unit with:
- **State management**: Maintains internal state as string
- **Connections**:
  - `input_connection`: List of (sender_id, keyword) tuples
  - `output_connection`: List of (keyword, receiver_id) tuples
- **Message queue**: Async queue for incoming messages
- **Frequency tracking**: Per-agent and per-keyword activation frequency
- **LLM integration**: OpenAI API integration for semantic processing

#### 2. MessageBus (`driver/agent_system.py`)

Central message routing with global controls:
- Routes messages between agents by ID
- **Global controls**:
  - `pause_messages()` / `resume_messages()`: Pause/resume all message flow
  - `set_message_delay(seconds)`: Add delay between messages
  - `set_speed_factor(factor)`: Speed control (1.0=normal, 0.1=slow)

#### 3. AgentSystem (`driver/agent_system.py`)

Orchestrator managing:
- All registered agents
- MessageBus instance
- I/O agents list
- Global system controls (pause/resume/speed)

### Agent Types

1. **Agent** (`driver/agent.py`): Standard LLM-powered processing agent
2. **InputAgent** (`driver/i_o_agent.py`): Abstract base for external input sources
3. **OutputAgent** (`driver/i_o_agent.py`): Abstract base for external output destinations
4. **InputOutputAgent** (`driver/i_o_agent.py`): Common base class with connection protection

### AgentNetwork (`driver/net.py`)

Manages Agent topology:
- Creates networks of agents with random connections
- Connects I/O agents to the network
- Tracks connection statistics

### Terminal Integration (`AVBash/`)

- **Terminal**: Multi-window bash terminal using pty
- **TerminalPair**: Input/Output agent pair for terminal interaction
- Commands: `/enter`, `/new`, `/kill`, `/focus`, `/scroll`, `/search`, `/list`

## Connection System

### Connection Structure

- **Input connection**: `(sender_id, keyword)` - Receive messages matching keyword from sender
- **Output connection**: `(keyword, receiver_id)` - Send messages to receiver when using keyword

### Protected Connections

Connections can be marked as "protected" with `[受保护]` prefix:
- Protected connections cannot be deleted by other agents
- Used for system connections (e.g., terminal I/O)

### Connection Management

Agents can modify connections via signals:
- **ACCEPT_INPUT**: Modify input connection keyword
- **REJECT_INPUT**: Delete input connection
- **SET_OUTPUT**: Modify output connection keyword
- **REJECT_OUTPUT**: Delete output connection

## Logging System

### Unified Logger (`utils/visual_monitor/unified_logger.py`)

All logs output as JSONL to `logs/system.jsonl`:

```json
{
  "timestamp_us": 1234567890123456,
  "level": "info",
  "source": "Agent.xxxxxx",
  "event_type": "message_received",
  "data": {...},
  "async_context": {...}
}
```

### Log Modes (LogMode)

- **CONTENT**: Basic events only
- **DETAIL**: Include object references
- **ARCH**: Include full async context (tasks, event loops)

Set via: `unified_logger.set_mode(LogMode.ARCH)`

### Loggable Base Class

All major classes inherit from `Loggable`:
- `info()`, `debug()`, `warning()`, `error()` - Standard levels
- `detail()` - Detailed program flow
- `arch()` - Architecture reconstruction data

## Signal System

Agents communicate via XML-like tags in LLM responses:

- `<self_state>...</self_state>`: Update internal state
- `<signal>{"content": [...]}</signal>`: Send control signals
- `<keyword>...</keyword>`: Send message to connected agents

### Signal Types

| Signal | Description |
|--------|-------------|
| `ACCEPT_INPUT` | Modify input connection keyword (old_keyword → new_keyword) |
| `REJECT_INPUT` | Delete input connection by keyword |
| `SET_OUTPUT` | Modify output connection keyword (old_keyword → new_keyword) |
| `REJECT_OUTPUT` | Delete output connection by keyword |

## Commands

### Run the System

```bash
# Main application (with terminal and web monitor)
python main.py

# Visual monitor server only
python -m utils.visual_monitor

# Standalone terminal
python -m AVBash
```

### Environment Setup

Requires environment variables (typically via `.env` file):
- `OPENAI_API_KEY`: API key for LLM access
- `OPENAI_BASE_URL`: Base URL for the API
- `OPENAI_MODEL`: Model name (default: gpt-3.5-turbo)

## Key Configuration Files

- `driver/pre_prompt.md`: Core agent programming instructions
- `logs/system.jsonl`: Unified JSONL log output
- `logs/agent_messages/`: Per-agent message logs

## Web Visualization Monitor

Real-time monitoring at `http://localhost:8765`:

- **Topology view**: Visual graph of agent connections
- **Message flow**: Real-time message traffic
- **Agent details**: Individual agent states and statistics
- **Async state**: Running tasks and event loop status
- **Log viewer**: Streaming log entries

### Monitor Server API

WebSocket messages:
- `type: topology_update` - Connection topology changed
- `type: message_flow` - New message sent
- `type: agent_activated` - Agent processed messages
- `type: async_update` - Task created/completed
- `type: log_entry` - Regular log entry

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

### Connection Philosophy
- Connections are evaluated like neuronal synapses
- Reinforce frequently activated, semantically coherent connections
- Prune low-activation or semantically irrelevant connections
- Split when state contains multiple independent semantic threads
