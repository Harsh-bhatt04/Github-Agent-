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
        "messages": [
            HumanMessage(content=user_request)
        ],
        "action": "",
        "arguments": {},
        "approval": False,
        "result": "",
    }

    result = graph.invoke(
        initial_state,
        config,
    )

    while "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value

        if interrupt_data["type"] == "commit_message":

            print("\n========== COMMIT MESSAGE ==========")
            print(interrupt_data["message"])
            print("=====================================")

            answer = input("\nCommit message: ")

            result = graph.invoke(
                Command(resume=answer),
                config,
            )

        elif interrupt_data["type"] == "approval":

            print("\n========== APPROVAL REQUIRED ==========")
            print(f"Action: {interrupt_data['action']}")
            print(f"Arguments: {interrupt_data['arguments']}")
            print(f"Message: {interrupt_data['message']}")
            print("=======================================")

            answer = input(
                "\nApprove? (yes/no): "
            ).strip().lower()

            result = graph.invoke(
                Command(resume=answer == "yes"),
                config,
            )

    print("\n========== RESULT ==========")
    print(result.get("result", ""))
    print("============================")


if __name__ == "__main__":
    main()