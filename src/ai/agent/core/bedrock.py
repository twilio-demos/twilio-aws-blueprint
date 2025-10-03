from langchain_aws import ChatBedrockConverse


class BedrockClientFactory:
    DEFAULT_MODEL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    AWS_REGION = "us-east-1"
    guardrail_id = "9tkyn5erdp9o"
    guardrail_version = "DRAFT"

    @staticmethod
    def get_latency_optimized_llm_with_guardrails():
        llm_with_guardrails = ChatBedrockConverse(
            model=BedrockClientFactory.DEFAULT_MODEL,
            temperature=0,
            max_tokens=4000,
            region_name=BedrockClientFactory.AWS_REGION,
            performance_config={
                "latency": "optimized",
            },
            guardrails={
                "guardrailIdentifier": BedrockClientFactory.guardrail_id,
                "guardrailVersion": BedrockClientFactory.guardrail_version,
                "trace": "enabled",
            },
        )
        return llm_with_guardrails
