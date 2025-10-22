from langchain_aws import ChatBedrockConverse

from src.ai.agent.core.agent_config import agent_config


class BedrockClientFactory:
    @staticmethod
    def get_latency_optimized_llm_with_guardrails():
        # Prepare base configuration
        llm_config = {
            "model": agent_config.model_name,
            "temperature": agent_config.temperature,
            "max_tokens": agent_config.max_tokens,
            "region_name": agent_config.region_name,
            "performance_config": {
                "latency": "optimized",
            },
        }

        # Add guardrails configuration only if guardrail_id is provided
        if agent_config.guardrail_id:
            llm_config["guardrails"] = {
                "guardrailIdentifier": agent_config.guardrail_id,
                "guardrailVersion": agent_config.guardrail_version,
                "trace": agent_config.guardrail_trace,
            }
            llm_config["guard_last_turn_only"] = agent_config.guard_last_turn_only

        llm_with_guardrails = ChatBedrockConverse(**llm_config)
        return llm_with_guardrails
