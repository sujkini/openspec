# gs-speckit — OpenSpec Custom Schema

A custom OpenSpec schema that brings the [GS Spec Kit workflow](https://github.com/chirag-wrk/gs-workflow) into OpenSpec's fluid, artifact-guided framework.

## What This Is

This schema implements a 6-artifact, gated workflow for specification-driven development:

```
validation → specs → repo-assessment → constitution → plan → tasks → apply
```

Each artifact has a **mandatory approval gate** — the AI agent will pause after creating each artifact and ask you to approve before proceeding.

## Origin

This workflow was originally built for the Ambient Code Platform using GitHub Spec Kit conventions. It has been adapted to work within OpenSpec's schema system while preserving:

- The full GS workflow structure (Stage 0 through Stage 5)
- User stories with priorities (P1/P2/P3)
- Repository assessment as a formal artifact
- 9-section technical implementation plans
- Execution backlogs with dependency DAGs, complexity scoring, and per-task payloads
- Per-task user validation during implementation

## Installation

### Option 1: Copy into your project

```bash
cp -r schemas/gs-speckit/ your-project/openspec/schemas/gs-speckit/
cp config.yaml your-project/openspec/config.yaml
cd your-project
openspec update
```

### Option 2: In a fresh project

```bash
cd your-project
openspec init
# Copy the schema
cp -r /path/to/new-openspec/schemas/gs-speckit/ openspec/schemas/gs-speckit/
# Set it as default
cp /path/to/new-openspec/config.yaml openspec/config.yaml
openspec schema validate gs-speckit
openspec update
```

## Usage

### Full pipeline (fast-forward all planning artifacts)

```
/opsx:propose "PROJ-1234: Add certificate rotation for webhook serving certs"
```

### Step-by-step (recommended — respects gates)

```
/opsx:new add-cert-rotation
/opsx:continue          → validation.md    [GATE: approve/reject]
/opsx:continue          → specs/           [GATE: approve/reject]
/opsx:continue          → repo-assessment  [GATE: approve/reject]
/opsx:continue          → constitution     [GATE: approve/reject]
/opsx:continue          → plan.md          [GATE: approve/reject]
/opsx:continue          → tasks.md         [GATE: approve/reject]
/opsx:apply             → implement (per-task validation)
/opsx:archive           → merge specs, archive change
```

### Explore before committing

```
/opsx:explore           → think through ideas, no artifacts yet
```

## Artifact Dependency Graph

```
              validation
              (no deps)
                  │
                  ▼
               specs
          (requires: validation)
                  │
                  ▼
          repo-assessment
          (requires: specs)
                  │
                  ▼
           constitution
     (requires: repo-assessment)
                  │
                  ▼
               plan
     (requires: specs + constitution
              + repo-assessment)
                  │
                  ▼
              tasks
          (requires: plan)
                  │
                  ▼
              APPLY
          (requires: tasks)
```

## Files

```
schemas/gs-speckit/
├── schema.yaml                  # Workflow definition + gate instructions
└── templates/
    ├── validation.md            # Spec quality gate (scoring template)
    ├── spec.md                  # Feature spec (user stories, FR-xxx, scenarios)
    ├── repo-assessment.md       # Repo analysis (target files, guardrails, risks)
    ├── constitution.md          # Project principles (from repo conventions)
    ├── plan.md                  # Technical plan (9 sections)
    ├── tasks.md                 # Execution backlog (DAG, checkboxes, payloads)
    └── checklist.md             # Quality checklist
```

## Differences from Original GS Workflow (on Ambient)

| Aspect | GS on Ambient | gs-speckit on OpenSpec |
|--------|--------------|----------------------|
| Jira access | Auto via MCP | User pastes ticket content |
| Gates | Hard-enforced by platform | Soft-enforced via agent instructions |
| Agent routing | Multi-agent (provisional IDs) | Single agent |
| Going back | Reject → revise loop only | Edit any file + continue |
| After completion | Repo merge | /opsx:archive (specs persist) |
| Parallel features | One pipeline | Multiple changes simultaneously |

## Customization

Edit `config.yaml` to inject project-specific context and per-artifact rules:

```yaml
schema: gs-speckit

context: |
  Your project-specific details here

rules:
  specs:
    - Your custom rules for specs
  plan:
    - Your custom rules for planning
```

## Validation

```bash
openspec schema validate gs-speckit
```
