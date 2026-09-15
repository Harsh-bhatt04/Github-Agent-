from langgraph.types import Command

from app.graph import graph


def main():
    user_request = input("What do you want to do? ")

    config = {
        "configurable": {
            "thread_id": "github-agent-1"
        }
    }

    state = {
        "user_request": user_request,
        "files": [],
        "approval": False,
        "result": "",
    }

    result = graph.invoke(state, config)

    # Graph paused at interrupt()
    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value

        print("\nHuman approval required:")
        print(f"Action: {interrupt_data['action']}")
        print(f"Files: {interrupt_data['files']}")
        print(f"Message: {interrupt_data['message']}")

        answer = input("\nApprove? (yes/no): ").strip().lower()

        approved = answer == "yes"

        result = graph.invoke(
            Command(resume=approved),
            config,
        )

    print("\nResult:")
    print(result.get("result", "Operation cancelled."))


if __name__ == "__main__":
    main()