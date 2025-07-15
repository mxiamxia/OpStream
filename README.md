# OpStream: Asynchronous AI Workflow Orchestration Platform

OpStream revolutionizes how users interact with AI tools by eliminating passive waiting during long-running operations. It provides an asynchronous, persistent AI orchestration system that manages complex workflows while keeping users informed through Slack notifications.

## 🚀 Vision

Traditional AI tools force users to wait passively during long operations like application profiling, system analysis, or complex deployments. OpStream changes this paradigm by:

- **Eliminating Passive Waiting**: Long-running workflows execute in the background
- **Persistent Memory**: Context and history maintained across sessions to reduce redundant work and token usage
- **Smart Orchestration**: MCP manages workflow state, tool interactions, and cross-component communication
- **Slack Integration**: Users receive notifications and interact only when human input is required
- **True Automation**: Fulfills the original promise of AI by actually freeing humans from mundane monitoring tasks

## 🏗️ Architecture

### Original Design Diagram

<img src="docs/architecture-diagram.png" alt="OpStream Architecture Flow" width="600" style="transform: rotate(90deg); transform-origin: center;">

*Original hand-drawn architecture showing the flow from Q0 (user query) through Slack interface, scheduler, MCP tools, LLM agent, to persistent storage.*

Based on the design flow diagram above, OpStream follows this orchestration pattern:

```
                            ┌─────────────────┐
                            │      Q0         │ ◄─── Initial User Query
                            │    (Query)      │
                            └─────────┬───────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │     Slack       │ ◄─── User Interface Layer
                            │   Interface     │
                            └─────────┬───────┘
                                      │
                                      ▼
                 ┌────────────────────────────────────────┐
                 │          Notification &                │
                 │         MCP Scheduler                  │ ◄─── Workflow Coordination
                 └──────────┬─────────────────────────────┘
                            │
                            ▼
             ┌─────────────────────────────────────────────────┐
             │                Scheduler                        │
             │              (Async Executor)                   │ ◄─── Background Processing
             └──────────┬──────────────────────┬───────────────┘
                        │                      │
                        ▼                      ▼
              ┌─────────────────┐    ┌─────────────────┐
              │      MCP        │    │      LLM        │ ◄─── Execution Layer
              │   Tool Layer    │    │   Agent Core    │
              └─────────┬───────┘    └─────────┬───────┘
                        │                      │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌─────────────────┐
                        │      DB         │ ◄─── Persistence Layer
                        │  (State Store)  │
                        └─────────────────┘
```

### Component Flow Details

1. **Q0 (Initial Query)**: User initiates workflow through Slack command
2. **Slack Interface**: Parses commands, manages user interactions, sends notifications
3. **Notification & MCP Scheduler**: Routes workflows, manages async execution queue
4. **Scheduler**: Background task executor that runs workflows without blocking users
5. **MCP Tool Layer**: Existing CloudWatch AppSignals tools (unmodified)
6. **LLM Agent Core**: AI reasoning engine that interprets results and makes decisions
7. **DB (State Store)**: Persistent storage for workflow state, memory, and results

### Key Design Principles from Diagram

- **Asynchronous Flow**: Users don't wait for long-running operations
- **Persistent State**: All workflow progress saved to database
- **Tool Isolation**: MCP tools remain unchanged, wrapped by scheduler
- **AI-Driven**: LLM agent provides intelligent analysis and decision-making
- **Notification-Based**: Users informed via Slack when attention needed

## 🔧 Core Components

### 1. Workflow Orchestrator (`/workflow`)
The heart of OpStream that manages long-running AI workflows:

- **Workflow Engine**: Coordinates tool execution, state transitions, and error handling
- **State Management**: Persists workflow progress, intermediate results, and recovery points
- **Session Manager**: Maintains LLM context and memory across interactions
- **Tool Coordinator**: Manages parallel/sequential tool execution and dependency resolution
- **Progress Tracker**: Monitors task completion and estimates remaining time

### 2. MCP Integration (`/mcp`)
Leverages existing MCP tools without modification:

- **Tool Registry**: Dynamically discovers and registers available MCP tools
- **Execution Wrapper**: Adds persistence and async capabilities to synchronous MCP tools
- **Result Aggregator**: Collects and correlates outputs from multiple tool invocations
- **Error Handler**: Manages tool failures and retry strategies
- **Memory Integration**: Shares context between tools and maintains historical insights

### 3. Slack Bot (`/slackbot`)
Primary user interface for notifications and interactions:

- **Notification Engine**: Sends status updates, completion alerts, and error notifications
- **Interactive Commands**: Allows users to query status, modify workflows, and provide input
- **Rich Formatting**: Displays results with charts, tables, and actionable buttons
- **User Management**: Handles permissions, preferences, and notification settings
- **Webhook Integration**: Receives and processes Slack events and commands

### 4. Persistent Storage
Maintains state and memory across sessions:

- **Workflow State**: Current status, completed steps, pending actions
- **Session Memory**: LLM context, conversation history, learned patterns
- **Tool Results**: Cached outputs, artifacts, and analysis results
- **User Preferences**: Notification settings, preferred channels, schedules

## 🔄 Workflow Examples

### Example 1: Application Profiling
```
User → Slack: "/profile my-service for 2 hours"
                ↓
OpStream: Creates workflow → Notifies user → Starts profiling
                ↓
Background: Monitors metrics → Analyzes patterns → Detects issues
                ↓
2 hours later: "✅ Profiling complete! Found 3 performance bottlenecks"
                ↓
User: "Show me the details"
                ↓
OpStream: Displays analysis → Suggests fixes → Offers implementation
```

### Example 2: SLO Monitoring
```
OpStream: Detects SLO breach → Analyzes root cause → Correlates traces
                ↓
Slack: "🚨 Payment service SLO breached. Root cause: Database timeout"
                ↓
User: "Fix it automatically"
                ↓
OpStream: Scales database → Adjusts timeouts → Monitors recovery
                ↓
Slack: "✅ Issue resolved. SLO restored in 5 minutes"
```

## 🛠️ Implementation Strategy

### Phase 1: Core Infrastructure
1. **Workflow Engine**: Basic state management and tool coordination
2. **Slack Bot**: Command handling and notifications
3. **Storage Layer**: Simple JSON-based persistence
4. **MCP Wrapper**: Async execution layer for existing tools

### Phase 2: Intelligence Layer
1. **Memory System**: Context persistence and pattern recognition
2. **Smart Notifications**: Intelligent filtering and timing
3. **Auto-Resolution**: Simple automated responses to common issues
4. **Progress Prediction**: Time estimation and workflow optimization

### Phase 3: Advanced Features
1. **Multi-User Workflows**: Team coordination and handoffs
2. **Custom Workflows**: User-defined automation patterns
3. **External Integrations**: PagerDuty, Datadog, Grafana connections
4. **Analytics Dashboard**: Workflow performance and insights

## 🚦 Getting Started

### Prerequisites
- Python 3.8+
- Slack workspace with bot permissions
- AWS credentials (for CloudWatch AppSignals integration)
- MCP-compatible tools

### Quick Setup
```bash
# Clone and install
git clone <your-repo-url>
cd OpStream
pip install -e .

# Configure Slack
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_SIGNING_SECRET="your-secret"

# Configure AWS (if using CloudWatch integration)
export AWS_REGION="us-east-1"
export AWS_PROFILE="your-profile"

# Start OpStream
python -m opstream.main
```

### Slack Commands
```
/opstream start <workflow-type> <parameters>  # Start a new workflow
/opstream status [workflow-id]                # Check workflow status
/opstream pause <workflow-id>                 # Pause workflow
/opstream resume <workflow-id>                # Resume workflow
/opstream list                                # List active workflows
/opstream help                                # Show available commands
```

## 🔧 Configuration

### Workflow Definitions
```yaml
# config/workflows.yaml
workflows:
  application_profiling:
    name: "Application Performance Profiling"
    tools:
      - cloudwatch_metrics
      - trace_analysis
      - log_aggregation
    duration: "2h"
    notifications:
      - start
      - milestones
      - completion
      - errors
    
  slo_monitoring:
    name: "SLO Compliance Monitoring"
    tools:
      - slo_checker
      - alert_correlator
    schedule: "*/5 * * * *"  # Every 5 minutes
    auto_resolve: true
```

### Slack Integration
```yaml
# config/slack.yaml
bot:
  token: "${SLACK_BOT_TOKEN}"
  signing_secret: "${SLACK_SIGNING_SECRET}"
  
channels:
  default: "#ops-alerts"
  critical: "#incidents"
  
notifications:
  quiet_hours: "22:00-08:00"
  timezone: "UTC"
  max_frequency: "1/hour"  # Rate limiting
```

## 🧠 Memory and Learning

OpStream's memory system reduces token usage and improves efficiency by:

1. **Pattern Recognition**: Identifies recurring issues and suggests proven solutions
2. **Context Persistence**: Maintains workflow context across interruptions
3. **Historical Analysis**: Leverages past successes to optimize new workflows
4. **Smart Caching**: Avoids redundant tool calls for similar scenarios

## 🔒 Security Considerations

- **Credential Management**: Secure storage of API keys and tokens
- **Access Control**: Role-based permissions for workflow management
- **Audit Logging**: Complete trail of actions and decisions
- **Data Privacy**: Configurable data retention and sanitization

## 🤝 Contributing

OpStream is designed to be extensible:

1. **Custom Tools**: Add new MCP tools to the registry
2. **Workflow Types**: Define new workflow patterns
3. **Integrations**: Connect additional platforms and services
4. **Notifications**: Extend notification channels and formats

## 📈 Monitoring and Metrics

OpStream includes built-in observability:

- **Workflow Performance**: Success rates, execution times, resource usage
- **Tool Utilization**: Most/least used tools, error rates, optimization opportunities
- **User Engagement**: Command usage, notification preferences, satisfaction metrics
- **System Health**: Memory usage, storage growth, async queue status

## 🗺️ Roadmap

- **Q1 2025**: Core workflow engine and Slack integration
- **Q2 2025**: Memory system and intelligent notifications
- **Q3 2025**: Multi-platform support (Teams, Discord, etc.)
- **Q4 2025**: Advanced analytics and workflow optimization

---

*OpStream: Where AI workflows run in the background, and humans focus on what matters.*