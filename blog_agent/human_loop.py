"""Human-in-the-loop review and approval interface."""

import sys
import os
import readline


def human_review(draft: str) -> str | None:
    """
    Show draft to human and collect feedback.

    Blocks on stdin until human provides input.

    Returns:
        - None if human approves
        - str with feedback if human wants changes
        - Raises KeyboardInterrupt on Ctrl+C
    """
    # Check if stdin is interactive
    if not sys.stdin.isatty():
        print("⚠️  Non-interactive stdin detected.")
        print("📄 Draft preview (first 500 chars):")
        print(draft[:500])
        print("...")
        print("Since stdin is not interactive, draft was saved directly.")
        return None

    print("\n" + "─" * 60)
    print("📄 DRAFT FOR REVIEW")
    print("─" * 60)
    print(draft)
    print("─" * 60)

    print("\n🤖 You can respond with:")
    print("  approve          — save and finish")
    print("  change <text>    — fix specific things")
    print("  rewrite          — re-write with a different angle")
    print("  lint             — run quality diagnostics")
    print("  stop             — abort pipeline")
    print("  quit             — save as-is and stop")
    print()

    while True:
        try:
            response = input("Your feedback: ").strip()
        except KeyboardInterrupt:
            print("\n\nPipeline stopped.")
            sys.exit(0)

        if not response:
            print("Type a command (approve, change, rewrite, lint, stop).")
            continue

        cmd = response.lower().strip()

        if cmd == "approve":
            return None

        if cmd == "quit":
            print("Saving draft as-is (no edits applied).")
            return None

        if cmd == "stop" or cmd == "quit":
            print("Pipeline stopped.")
            sys.exit(0)

        if cmd == "rewrite":
            return "rewrite the entire piece with a different angle and stronger thesis"

        if cmd == "lint":
            from blog_agent.quality import lint
            print("\n" + "─" * 60)
            print("📊 QUALITY LINT")
            print("─" * 60)
            print(lint(draft))
            print("─" * 60)
            print("\nWhat would you like to do?\n")
            continue

        if cmd.startswith("change"):
            feedback = cmd[7:].strip() or "fix any issues you see"
            return feedback

        if len(response) > 10:
            return response

        print(f"Unknown command: '{cmd}'. Try: approve, change <feedback>, rewrite, lint, stop")
