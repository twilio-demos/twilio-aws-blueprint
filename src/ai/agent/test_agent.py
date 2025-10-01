# run_ai_agent_runner_test.py

import asyncio

from dotenv import load_dotenv

from src.ai.agent.core.agent_runner import AIAgentRunner

load_dotenv()


async def main():
    runner = AIAgentRunner()

    print("\n=== Test: stream_request ===")
    async for chunk in runner.stream_request(
        "Check account balance for Alice Smith on her checking account please. Date of birth is 03/15/1985."
    ):
        print("Stream chunk:", chunk)


if __name__ == "__main__":
    asyncio.run(main())
