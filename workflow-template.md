**Core Components of workflow.md**

**1\. The System Prompt & Agent Personas**

This is the exact, unvarnished text instruction given to the LLM. If your workflow uses multiple agents (e.g., a "Coder Agent" and a "Reviewer Agent"), document the prompt for each.

* **Role/Context:** Who the agent thinks it is (e.g., *"You are an automated OpenShift CI triage assistant..."*).  
* **Objectives:** What the agent is explicitly tasked to do.  
* **Guardrails:** Strict negative constraints (e.g., *"Do not attempt to merge code if unit tests fail,"* or *"Never expose internal API keys"*).

**2\. Orchestration Configuration (The State Machine)**

This explains how the agent moves from one step to the next. You need to document how the workflow flows.

* **Triggers:** What starts the agent? (e.g., A GitHub Issue creation, a Prow job failure).  
* **Sequential Steps:** A clear, step-by-step breakdown of the agent's logic loop.  
* **Branching/Conditional Logic:** What happens if the agent's output fails a validation check? Does it loop back and try again, or does it alert a human?

**3\. Tool & Building Block Integration**

An agent is only as good as the tools it can call. List the specific "building blocks" (from ai-helpers or custom scripts) that this workflow exposes to the LLM.

* **Read Tools:** (e.g., get\_issue\_comments, fetch\_repo\_structure)  
* **Write/Action Tools:** (e.g., create\_pull\_request, run\_prow\_job)

**4\. Input/Output Schema & Variables**

Document how data is passed into the prompt and what format is expected back.

* **Inputs:** Dynamic variables injected into the prompt (e.g., ${ISSUE\_BODY}, ${FAILED\_LOG\_SNIPPET}).  
* **Expected Output:** Is the agent forced to output in a specific structured format like JSON or a specific Markdown template so the orchestration layer can parse it?

**5\. Version History & Evolution (The "Versioned" Aspect)**

Since the prompt/config is "versioned," include a brief changelog at the bottom or top of the file. Executives love to see iteration.

* *Example:* **v1.0** (Basic prompt, high hallucination rate) $\\rightarrow$ **v1.1** (Added strict JSON schema parsing) $\\rightarrow$ **v1.2** (Integrated ai-helpers library for git operations).

