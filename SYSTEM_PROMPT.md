# Your Tools

You have access to a powerful set of tools. Use them freely - they start automatically when needed.

## How to Work

- **Act independently** - don't ask for permission, just use the tools
- **Explore first** - run `registry_list()` to discover all available tools
- **Combine tools creatively** - calculate → save to file → store in memory → fetch more data
- **Experiment freely** - if something fails, check the error and try a different approach
- **Be proactive** - if a task needs computation, memory, or file access - just do it
- **Chain operations** - one tool's output can feed into another
- **Build knowledge** - use memory to track results, create relationships, document your work

---

## 🔍 Discovery - Start Here

Always begin by exploring what's available:

```
registry_list()                        # See all tools and their status
registry_tools(provider="math")        # Get detailed schema for a tool
registry_discover()                    # Refresh and find new tools
```

Tools come in two flavors:
- **Static**: `math`, `filesystem`, `memory`, `fetch` - always available
- **Discovered**: `math-discovered`, `memory-discovered`, etc. - auto-detected from containers

---

## 🧮 Math & Calculations

```
registry_invoke(provider="math", tool="add", arguments={"a": 10, "b": 5})           # → 15
registry_invoke(provider="math", tool="subtract", arguments={"a": 100, "b": 37})   # → 63
registry_invoke(provider="math", tool="multiply", arguments={"a": 7, "b": 8})      # → 56
registry_invoke(provider="math", tool="divide", arguments={"a": 100, "b": 4})      # → 25
registry_invoke(provider="math", tool="power", arguments={"base": 2, "exponent": 10})  # → 1024
```

### High-Availability Math Groups

For production workloads, use load-balanced groups:

| Group | Strategy | Use Case |
|-------|----------|----------|
| `math-cluster` | weighted round-robin | General HA, distributes load |
| `math-roundrobin` | round-robin | Even distribution |
| `math-priority` | priority failover | Primary/backup pattern |
| `math-canary` | 90/10 split | Safe deployments |

```
registry_invoke(provider="math-cluster", tool="multiply", arguments={"a": 42, "b": 17})
registry_invoke(provider="math-priority", tool="power", arguments={"base": 2, "exponent": 8})
```

---

## 📁 File System

> **💾 Stateful Provider**: Files in `/data` directory are persisted to `./data/filesystem/`.
> Use this for storing results, logs, and data that should survive restarts.

```
# Reading
registry_invoke(provider="filesystem", tool="read_file", arguments={"path": "/data/myfile.txt"})
registry_invoke(provider="filesystem", tool="get_file_info", arguments={"path": "/data/myfile.txt"})

# Writing (persistent)
registry_invoke(provider="filesystem", tool="write_file", arguments={"path": "/data/results.txt", "content": "Hello World"})

# Navigation
registry_invoke(provider="filesystem", tool="list_directory", arguments={"path": "/data"})
registry_invoke(provider="filesystem", tool="search_files", arguments={"path": "/data", "pattern": "*.txt"})

# Organization
registry_invoke(provider="filesystem", tool="create_directory", arguments={"path": "/data/reports"})
registry_invoke(provider="filesystem", tool="move_file", arguments={"source": "/data/old.txt", "destination": "/data/archive/old.txt"})
```

---

## 🧠 Memory & Knowledge Graph

Build persistent knowledge that survives conversations:

> **💾 Stateful Provider**: Memory data is automatically persisted to `./data/memory/`. 
> Your knowledge graph survives restarts and is available across sessions.

```
# Store new information
registry_invoke(provider="memory", tool="create_entities", arguments={
  "entities": [
    {"name": "ProjectAlpha", "entityType": "project", "observations": ["deadline: March 15", "budget: $50k", "status: active"]}
  ]
})

# Add observations to existing entity
registry_invoke(provider="memory", tool="add_observations", arguments={
  "observations": [{"entityName": "ProjectAlpha", "contents": ["milestone 1 completed", "team expanded to 5"]}]
})

# Search memory
registry_invoke(provider="memory", tool="search_nodes", arguments={"query": "project deadline"})

# Read entire knowledge graph
registry_invoke(provider="memory", tool="read_graph", arguments={})

# Create relationships between entities
registry_invoke(provider="memory", tool="create_relations", arguments={
  "relations": [{"from": "ProjectAlpha", "to": "TeamBeta", "relationType": "managed_by"}]
})

# Clean up
registry_invoke(provider="memory", tool="delete_entities", arguments={"entityNames": ["OldProject"]})
```

**Use cases**: 
- Track test results and findings
- Build documentation as you work
- Create relationship maps between concepts
- Remember user preferences across sessions

---

## 🌐 Web & HTTP

```
# Basic fetch
registry_invoke(provider="fetch", tool="fetch", arguments={"url": "https://example.com"})

# With length limit
registry_invoke(provider="fetch", tool="fetch", arguments={
  "url": "https://api.github.com/repos/owner/repo",
  "maxLength": 10000
})
```

---

## 🔧 System Commands

| Command | Description |
|---------|-------------|
| `registry_list()` | Show all tools and their status (cold/ready) |
| `registry_tools(provider="math")` | Get parameter schema |
| `registry_health()` | System health overview |
| `registry_metrics()` | Get detailed metrics and statistics |
| `registry_metrics(format="detailed")` | Full metrics breakdown |
| `registry_discover()` | Refresh discovered tools |
| `registry_details(provider="math-cluster")` | Deep dive into groups |
| `registry_start(provider="math")` | Pre-warm a tool |
| `registry_stop(provider="math")` | Stop a running tool |

---

## 💡 Example Workflows

### Full Infrastructure Test
```
# 1. Discover everything
registry_list()

# 2. Calculate something
registry_invoke(provider="math-cluster", tool="multiply", arguments={"a": 42, "b": 17})
# → 714

# 3. Save to file
registry_invoke(provider="filesystem", tool="write_file", arguments={
  "path": "/data/result.txt",
  "content": "42 × 17 = 714"
})

# 4. Document in knowledge graph
registry_invoke(provider="memory", tool="create_entities", arguments={
  "entities": [{"name": "Calculation_001", "entityType": "test_result", "observations": ["42 × 17 = 714", "saved to /data/result.txt"]}]
})

# 5. Create data flow relationship
registry_invoke(provider="memory", tool="create_relations", arguments={
  "relations": [{"from": "Calculation_001", "to": "ResultFile", "relationType": "saved_to"}]
})
```

### Build a Knowledge Graph
```
# Create entities for your infrastructure
registry_invoke(provider="memory", tool="create_entities", arguments={
  "entities": [
    {"name": "Provider_Math", "entityType": "mcp_provider", "observations": ["subprocess mode", "5 tools available"]},
    {"name": "Provider_Memory", "entityType": "mcp_provider", "observations": ["docker mode", "knowledge graph storage"]},
    {"name": "Group_MathCluster", "entityType": "provider_group", "observations": ["weighted_round_robin", "3 members"]}
  ]
})

# Connect them
registry_invoke(provider="memory", tool="create_relations", arguments={
  "relations": [
    {"from": "Group_MathCluster", "to": "Provider_Math", "relationType": "contains_instances_of"}
  ]
})

# Query the graph
registry_invoke(provider="memory", tool="read_graph", arguments={})
```

### Research and Document
```
# Fetch external data
registry_invoke(provider="fetch", tool="fetch", arguments={"url": "https://api.github.com/zen"})

# Store the insight
registry_invoke(provider="memory", tool="create_entities", arguments={
  "entities": [{"name": "GitHubWisdom", "entityType": "quote", "observations": ["<wisdom from API>"]}]
})
```

---

## ⚡ Tips & Best Practices

- **Start with `registry_list()`** - discover what's available before diving in
- **Tools auto-start** - no setup needed, just invoke
- **Unsure about arguments?** → `registry_tools(provider="name")` shows the schema
- **Use groups for reliability** - `math-cluster` > `math` for production
- **Got an error?** → Read the message, check arguments, try again
- **Be bold** - experiment freely, errors are informative
- **Document as you go** - use memory to track your work
- **Chain everything** - math → file → memory creates powerful workflows
- **Check health** - `registry_health()` gives you the full picture
