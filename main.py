import asyncio

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph import build_graph


async def main():
    graph = await build_graph()

    user_request = input("What do you want to do? ").strip()

    if not user_request:
        print("No request provided.")
        return

    config = {
        "configurable": {
            "thread_id": "github-agent-1"
        }
    }

    state = {
        "messages": [
            HumanMessage(content=user_request)
        ],
        "action": "",
        "arguments": {},
        "tool_call_id": "",
        "approval": False,
        "result": "",
    }

    result = await graph.ainvoke(
        state,
        config,
    )

    while "__interrupt__" in result:

        interrupt_data = result["__interrupt__"][0].value

        interrupt_type = interrupt_data.get("type")

        if interrupt_type == "commit_message":

            while True:
                message = input(
                    "Commit message: "
                ).strip()

                if message:
                    break

                print("Commit message cannot be empty.")

            result = await graph.ainvoke(
                Command(resume=message),
                config,
            )

        elif interrupt_type == "approval":

            action = interrupt_data["action"]
            arguments = interrupt_data["arguments"]

            print("\n--------------------------------")
            print("Human Approval Required")
            print("--------------------------------")
            print(f"Action: {action}")
            print(f"Arguments: {arguments}")

            answer = input(
                "Approve? (yes/no): "
            ).strip().lower()

            approved = answer in {
                "yes",
                "y",
            }

            result = await graph.ainvoke(
                Command(resume=approved),
                config,
            )

        else:
            print(
                "Unknown interrupt:",
                interrupt_data,
            )
            return

    if result.get("result"):
        print("\nResult:")
        print(result["result"])
        return

    # If the agent simply responded without using a tool.
    messages = result.get("messages", [])

    if messages:
        last_message = messages[-1]

        if hasattr(last_message, "content"):
            print("\nAgent:")
            print(last_message.content)


if __name__ == "__main__":
    asyncio.run(main())