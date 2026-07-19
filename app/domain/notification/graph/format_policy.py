def format_policy(policies: list[dict]) -> str:

    policies_text = "\n\n".join(f"### {policy['service_name']} (ID: {policy['service_id']})\n"
                                + "\n".join(f"[{ct}]\n{policy_content}" for ct, policy_content in policy.items())
                                for policy in policies)

    return policies_text