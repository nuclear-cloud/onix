# Agent Workflow Instructions

## Core Rule: Discuss First, Execute Second
**Priority**: CRITICAL

The user has explicitly requested a strict workflow where we **must** discuss and agree on a plan before writing any code.

### The Protocol

1.  **Analyze**: Read the user's request and explore the codebase (using `ls`, `cat`, grep`) to understand the context.
2.  **Propose Initial Plan**: Create or update `implementation_plan.md` with a detailed proposal.
3.  **Iterate & Refine (CRITICAL)**: Present the plan to the user.
    *   **Loop**: Ask for feedback. Modify the plan. Present again.
    *   **Continue this loop specifically until the user says the plan is "Perfect" or explicitly approves it.**
    *   Do NOT proceed if the user has questions or doubts.
4.  **Execute**: Only start using `write_to_file` (code), `replace_file_content`, or `run_command` **AFTER** strict final approval.

### Allowed Actions at Any Time
- Reading files.
- Listing directories.
- Searching code.
- Checking documentation.

### Prohibited Actions Before Approval
- Overwriting files.
- Creating new files (except this instruction file or plans).
- Running shell commands that modify state.

## Development Standards

### 1. Mandatory Unit Tests
**Rule**: Any new feature or bug fix **MUST** be accompanied by unit tests located in the `tests/` directory. No code should be considered complete without verification.

### 2. File Concept Header
**Rule**: Every file in the project **MUST** start with a simple, high-level explanation of its "Concept". 
- Use a comment block at the top.
- Explain **WHAT** the file does and **WHY** it exists in simple terms.
- Avoid technical jargon where possible in this header.

### 3. Language & Localization
**Priority**: HIGH
**Rule**: The system is oriented toward the **Ukrainian market**. 
- **Development**: All internal code, comments, documentation headers, and internal logs **MUST** be in English.
- **User/Database**: All user-facing strings, API error messages, and database-stored content (e.g., default descriptions) **MUST** be in Ukrainian.
