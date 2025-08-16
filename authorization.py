import json
from typing import List, Dict, Any

class AuthorizationManager:
    _pending_authorizations: List[Dict[str, Any]] = []
    _authorized_calls: List[Dict[str, Any]] = []

    @classmethod
    def add_pending_authorization(cls, tool_call: Dict[str, Any]):
        """Adds a tool call to the list of pending authorizations."""
        # Ensure a unique ID or some way to reference it later
        # For simplicity, we'll just append it for now.
        # In a real system, you'd want a more robust queuing mechanism.
        cls._pending_authorizations.append(tool_call)

    @classmethod
    def get_pending_authorizations(cls) -> List[Dict[str, Any]]:
        """Returns all currently pending authorizations."""
        return list(cls._pending_authorizations)

    @classmethod
    def clear_pending_authorizations(cls):
        """Clears all pending authorizations. Useful after retrieval."""
        cls._pending_authorizations.clear()

    @classmethod
    def post_authorization_decision(cls, decision: Dict[str, Any]) -> bool:
        """
        Receives an authorization decision for a tool call.

        Args:
            decision: A dictionary containing the original tool call and the decision.
                      Example: {"tool_call": {...}, "action": "approve"|"deny"|"modify", "new_args": {...}}

        Returns:
            True if the decision was processed successfully, False otherwise.
        """
        tool_call_original = decision.get("tool_call")
        action = decision.get("action")
        new_args = decision.get("new_args")

        if not tool_call_original or not action:
            return False

        # Find and remove the original tool_call from pending, then add to authorized_calls
        # This simulation assumes that the decision comes with the original tool_call data.
        # In a real API, you'd likely use an ID to reference the pending item.

        # Simple approach: remove all matching tool_calls from pending (assuming no duplicates or specific IDs)
        # More robust approach would be to assign unique IDs to pending requests.
        initial_pending_count = len(cls._pending_authorizations)
        cls._pending_authorizations = [
            tc for tc in cls._pending_authorizations if tc != tool_call_original
        ]
        if len(cls._pending_authorizations) == initial_pending_count:
            # The tool_call_original was not found in pending, maybe it was already processed or is invalid.
            print(f"Warning: Tool call not found in pending authorizations for decision: {tool_call_original}")
            # For this simulation, we'll still try to process the decision even if not found in pending
            # as it might represent a direct decision without prior pending state.

        processed_call = tool_call_original.copy()

        if action == 'approve':
            # No change needed if approved without modification
            cls._authorized_calls.append(processed_call)
            return True
        elif action == 'deny':
            processed_call["denied"] = True
            cls._authorized_calls.append(processed_call)
            return True
        elif action == 'modify' and new_args is not None:
            processed_call["args"] = new_args
            cls._authorized_calls.append(processed_call)
            return True
        else:
            print(f"Error: Invalid action '{action}' or missing new_args for 'modify'.")
            return False

    @classmethod
    def get_authorized_calls(cls) -> List[Dict[str, Any]]:
        """Returns all calls that have been authorized (or denied)."""
        return list(cls._authorized_calls)

    @classmethod
    def reset(cls):
        """Resets the manager's state for testing purposes."""
        cls._pending_authorizations = []
        cls._authorized_calls = []

# Example usage (for testing purposes, not part of the 'endpoint' itself)
if __name__ == "__main__":
    print("AuthorizationManager Demonstration:")

    # Reset for a clean demo
    AuthorizationManager.reset()

    # Simulate a tool call that needs authorization
    sample_tool_call_1 = {
        "tool_name": "run_command",
        "args": {"command": "ls -l /"},
        "call_id": "abc-123"
    }
    sample_tool_call_2 = {
        "tool_name": "read_file",
        "args": {"path": "/etc/passwd"},
        "call_id": "def-456"
    }

    print("\nAdding pending authorizations...")
    AuthorizationManager.add_pending_authorization(sample_tool_call_1)
    AuthorizationManager.add_pending_authorization(sample_tool_call_2)

    print("\n--- GET /authorize (simulated) ---")
    pending = AuthorizationManager.get_pending_authorizations()
    print("Pending authorizations:", json.dumps(pending, indent=2))

    # Simulate decision for sample_tool_call_1 (approve)
    decision_1 = {
        "tool_call": sample_tool_call_1,
        "action": "approve"
    }
    print(f"\n--- POST /authorize (approve decision) ---")
    success = AuthorizationManager.post_authorization_decision(decision_1)
    print(f"Decision processed: {success}")

    # Simulate decision for sample_tool_call_2 (deny)
    decision_2 = {
        "tool_call": sample_tool_call_2,
        "action": "deny"
    }
    print(f"\n--- POST /authorize (deny decision) ---")
    success = AuthorizationManager.post_authorization_decision(decision_2)
    print(f"Decision processed: {success}")

    print("\n--- GET /authorize (after decisions) ---")
    pending_after = AuthorizationManager.get_pending_authorizations()
    print("Pending authorizations:", json.dumps(pending_after, indent=2)) # Should be empty if processed correctly

    print("\n--- Authorized Calls ---")
    authorized = AuthorizationManager.get_authorized_calls()
    print("Authorized/Denied calls:", json.dumps(authorized, indent=2))

    # Simulate a call with modification
    sample_tool_call_3 = {
        "tool_name": "write_file",
        "args": {"path": "/tmp/test.txt", "content": "hello"},
        "call_id": "ghi-789"
    }
    AuthorizationManager.add_pending_authorization(sample_tool_call_3)
    pending_before_mod = AuthorizationManager.get_pending_authorizations()
    print("\nPending before modify:", json.dumps(pending_before_mod, indent=2))

    modified_decision = {
        "tool_call": sample_tool_call_3,
        "action": "modify",
        "new_args": {"path": "/home/anubhav/courses/luna-version-x/output.txt", "content": "modified content"}
    }
    print(f"\n--- POST /authorize (modify decision) ---")
    success_mod = AuthorizationManager.post_authorization_decision(modified_decision)
    print(f"Modify decision processed: {success_mod}")

    print("\n--- Authorized Calls (after modify) ---")
    authorized_after_mod = AuthorizationManager.get_authorized_calls()
    print("Authorized/Denied calls:", json.dumps(authorized_after_mod, indent=2))
