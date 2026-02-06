# MCP Hangar Cookbook — Authoring Instructions

> These instructions govern the creation of all cookbook recipes in `docs/cookbook/`.
> Every recipe MUST follow this schema and these rules. No exceptions.

## Philosophy

The cookbook is a **progressive tutorial disguised as reference docs**. Recipes 01–06 form a linear path: each one adds exactly one capability to the setup from the previous recipe. Recipes 07+ are standalone but reference earlier recipes as prerequisites. The reader should be able to start at 01 and reach production-grade setup by 13 without reading anything else.

**Core principle:** Show, don't explain. Config block first, wall of text never.

## Recipe Schema

Every recipe follows this exact structure. Do not add, remove, or reorder sections.

```markdown
# {NUMBER} — {TITLE}

> **Prerequisite:** {link to previous recipe or "None"}
> **You will need:** {concrete requirements: running Hangar, specific provider, etc.}
> **Time:** {realistic minutes, be honest}
> **Adds:** {one-line summary of what this recipe layers on}

## The Problem

{2-4 sentences max. Concrete scenario. Written as if the reader is experiencing it RIGHT NOW.
Use "you" not "the user". No hypotheticals — state the pain as fact.}

## The Config

{Complete, copy-pasteable config block. Not a diff, not a fragment — the FULL config
that works for this recipe. If it builds on a previous recipe, show the entire file
with the new additions marked with inline comments: `# NEW: added in this recipe`}

```yaml
# config.yaml — Recipe {NUMBER}: {TITLE}
providers:
  my-mcp:
    mode: remote
    endpoint: "http://localhost:8080"
    health_check:                    # NEW: added in this recipe
      endpoint: /health
      interval_s: 10
```

## Try It

{Numbered steps. Each step is ONE command + what you expect to see.
No explanatory prose between steps. Format:}

1. {action}

   ```bash
   {command}
   ```

   ```
   {expected output — exact or close approximation}
   ```

2. {action}

   ```bash
   {command}
   ```

   ```
   {expected output}
   ```

{Minimum 3 steps, maximum 8. If you need more, split into two recipes.}

## What Just Happened

{3-6 sentences explaining the mechanism. Technical but accessible.
Assume the reader knows what a reverse proxy is but not what a circuit breaker half-open state is.
Reference Hangar internals by name: "the registry", "the health monitor", "the circuit breaker".
Link to API docs or architecture docs where relevant.}

## Key Config Reference

{Table of every config key introduced in this recipe. Not all keys — only the NEW ones.}

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `health_check.endpoint` | string | — | HTTP path to probe |
| `health_check.interval_s` | int | `30` | Seconds between checks |

## What's Next

{1-2 sentences. Link to next recipe in the progression. Frame it as the natural next problem:
"Your provider is healthy — but what happens when it starts failing intermittently?
→ [03 — Circuit Breaker](03-circuit-breaker.md)"}

```

## File Naming

```

docs/cookbook/
├── index.md
├── 01-http-gateway.md
├── 02-health-checks.md
├── 03-circuit-breaker.md
├── 04-failover.md
├── 05-load-balancing.md
├── 06-rate-limiting.md
├── 07-observability-metrics.md
├── 08-observability-langfuse.md
├── 09-subprocess-providers.md
├── 10-discovery-docker.md
├── 11-discovery-kubernetes.md
├── 12-auth-rbac.md
├── 13-production-checklist.md

```

## index.md Structure

```markdown
# Cookbook

From zero to production in 13 recipes. Start at 01 and go in order,
or jump to what you need.

## The Path (sequential)

| # | Recipe | What it adds |
|---|--------|-------------|
| 01 | [HTTP Gateway](01-http-gateway.md) | Single MCP provider behind Hangar |
| 02 | [Health Checks](02-health-checks.md) | Know when your provider is dead |
| ... | ... | ... |

## Standalone Recipes

| # | Recipe | Prerequisite |
|---|--------|-------------|
| 09 | [Subprocess Providers](09-subprocess-providers.md) | 01 |
| ... | ... | ... |
```

## Writing Rules

### Tone

- **Direct and technical.** Not a blog post, not a marketing page.
- Second person: "you", "your provider", "your config".
- Present tense: "Hangar detects the failure" not "Hangar will detect the failure".
- No filler: remove "simply", "just", "easily", "Note that", "It's worth noting".
- No selling: never say "powerful", "robust", "enterprise-grade" in recipes. The config speaks.

### Config Blocks

- **Every recipe shows the COMPLETE config file**, not fragments or diffs.
- New additions marked with `# NEW: added in this recipe`.
- Config MUST be valid YAML that works if copy-pasted into `config.yaml`.
- Use realistic values: real ports (8080, 3000), real paths, real endpoint names.
- **Never use `example.com` or placeholder domains.** Use `localhost` with ports.
- Provider names should be consistent across recipes: the HTTP provider introduced in 01 is called `my-mcp` everywhere.

### Try It Steps

- Each step: one command, one expected output.
- Commands must actually work against the config shown above.
- Use `mcp-hangar` CLI commands, not curl or raw API calls (unless demonstrating something specific).
- Include the "break it" step where applicable: kill a process, flood with requests, revoke a token. The reader must see the failure AND the recovery.
- Expected output should be realistic — copy from actual `mcp-hangar` CLI output format.

### Cross-Recipe Continuity

- Recipes 01–06 use the SAME provider setup. The config grows, never resets.
- Provider name: `my-mcp` (HTTP provider used throughout sequential recipes)
- Provider URL: `http://localhost:8080`
- Group name (from 04): `my-mcp-group`
- Second provider (from 04): `my-mcp-backup` at `http://localhost:8081`
- Third provider (from 05): `my-mcp-3` at `http://localhost:8082`
- These names and ports are canonical. Do not invent new ones.

### Recipe 13 Exception

Recipe 13 (Production Checklist) does NOT follow the standard schema.
It uses a checklist format:

```markdown
# 13 — Production Checklist

> Before you go live, walk through this list.

## Security
- [ ] TLS termination configured
- [ ] API keys rotated from defaults
- [ ] RBAC scopes are least-privilege
...

## Reliability
- [ ] Health checks on all providers
- [ ] Circuit breakers configured
...
```

## Validation Checklist (run before committing any recipe)

- [ ] File name matches pattern: `{NN}-{slug}.md`
- [ ] All six sections present in order: Problem, Config, Try It, What Just Happened, Key Config Reference, What's Next
- [ ] Config block is complete (not a fragment) and valid YAML
- [ ] New config keys marked with `# NEW` comments
- [ ] Try It has 3–8 numbered steps with commands and expected output
- [ ] No forbidden words: "simply", "just", "easily", "powerful", "robust", "enterprise-grade", "Note that"
- [ ] Provider names match canonical names from cross-recipe continuity
- [ ] Prerequisite link points to correct previous recipe
- [ ] What's Next link points to correct next recipe
- [ ] Key Config Reference table only contains keys NEW to this recipe
