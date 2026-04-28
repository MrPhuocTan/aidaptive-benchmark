# AI Vibe Coding Workflow

This document outlines the workflow for AI agents (Cursor, Cline, Gemini, Antigravity, etc.) to utilize the context files in the `skills/` directory. By following this workflow, the AI saves tokens, reduces hallucination, and writes code perfectly aligned with the project's aesthetics and technical standards.

## The Vibe Coding Workflow

### 1. Initialization (Context Gathering)
Whenever the user prompts the AI to write a new feature, fix a bug, or refactor code, the AI MUST silently identify the domains involved:
- Is this a backend task? -> Read `skills/python-fastapi.md`
- Is this a frontend/UI task? -> Read `skills/frontend-html-js.md`
- *Note: In modern IDE agents, these rules can be loaded automatically via `.cursorrules` or similar mechanics.*

### 2. The Golden Rules of Vibe Coding
1. **Never repeat the prompt:** Do not waste tokens confirming what you are about to do. Acknowledge briefly and get to work.
2. **Atomic Changes:** Only output the exact code blocks or functions that need to change. Do not output the entire 1000-line file unless requested. Use `search/replace` diffs if your tooling supports it.
3. **No Placeholders:** Never use `// ... existing code ...` or `pass # TODO` unless specifically instructing the user to implement it. Provide complete, working snippets for the targeted area.
4. **Assume Competence:** You do not need to explain how `async/await` works or why you used a Tailwind class. Let the code speak for itself.

### 3. Execution Pattern
1. **Think:** Briefly analyze the problem.
2. **Vibe Check:** Does this solution align with the `skills/*.md` files? (Is it using Pydantic v2? Is it using Tailwind utilities properly?)
3. **Code:** Output the diff or the new file.
4. **Verify:** Are imports correct? Is it type-safe?

## Example Agent Prompt
If you are setting up a custom GPT or AI Agent, use this as the system prompt:
> "You are an expert developer. Before answering, review the files in the `skills/` directory of this workspace to adopt the required persona and coding standards. Follow the 'Tokens Saving Strategy' strictly. Talk less, code more."
