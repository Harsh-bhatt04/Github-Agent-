from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph import graph


def main():
    user_request = input("What do you want to do? ")

    config = {
        "configurable": {
            "thread_id": "github-agent-1",
        }
    }

    initial_state = {
        "messages": [HumanMessage(content=user_request)],
        "approval": False,
        "commit_message": "",
        "result": "",
    }

    result = graph.invoke(initial_state, config)

    # Agent needs more information
    last_message = result["messages"][-1]

    if not last_message.tool_calls and "commit message" in str(last_message.content).lower():
        commit_message = input("\nEnter commit message: ")

        result = graph.invoke(
            Command(
                resume=None,
                update={
                    "messages": [
                        HumanMessage(
                            content=f"Use this commit message: {commit_message}"
                        )
                    ]
                },
            ),
            config,
        )

    # Human approval
    if "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value

        print("\n========== APPROVAL REQUIRED ==========")
        print(f"Action: {interrupt_data['action']}")
        print(f"Arguments: {interrupt_data['arguments']}")
        print(f"Message: {interrupt_data['message']}")
        print("=======================================")

        answer = input("\nApprove? (yes/no): ").strip().lower()

        result = graph.invoke(
            Command(resume=answer == "yes"),
            config,
        )

    print("\n========== RESULT ==========")

    for message in result["messages"]:
        if message.content:
            print(message.content)

    print("============================")


if __name__ == "__main__":
    main()