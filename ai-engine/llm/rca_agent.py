# ai-engine/llm/rca_agent.py
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
from openai import AzureOpenAI

class RCAAgent:
    """
    Root Cause Analysis Agent using Azure OpenAI GPT-4.
    Analyzes logs, metrics, and traces to determine incident root cause.
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    
    async def analyze(
        self,
        incident_id: str,
        metrics: Dict[str, Any],
        logs: List[str],
        traces: Optional[List[Dict]] = None,
        similar_incidents: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive RCA using LLM.
        """
        
        # Prepare context for the LLM
        context = self._prepare_context(metrics, logs, traces, similar_incidents)
        
        # Create the RCA prompt
        prompt = self._create_rca_prompt(incident_id, context)
        
        # Call Azure OpenAI
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        
        return {
            "root_cause": result.get("root_cause", "Unknown"),
            "severity": result.get("severity", "medium"),
            "confidence": result.get("confidence", 0.0),
            "impact": result.get("impact_assessment", "Unknown impact"),
            "contributing_factors": result.get("contributing_factors", []),
            "timeline": result.get("timeline", []),
            "recommendations": result.get("recommendations", [])
        }
    
    def _get_system_prompt(self) -> str:
        """
        System prompt that defines the AI's role as an SRE expert.
        """
        return """You are an expert Site Reliability Engineer (SRE) and DevOps specialist with deep knowledge of:
- Kubernetes and container orchestration
- Cloud infrastructure (Azure, AWS, GCP)
- Application performance monitoring
- Distributed systems debugging
- Infrastructure as Code (Terraform, Helm)

Your task is to analyze incidents and provide:
1. Clear, concise root cause identification
2. Severity assessment (critical/high/medium/low)
3. Confidence score (0.0 to 1.0)
4. Impact assessment on users/services
5. Contributing factors
6. Incident timeline
7. Actionable remediation recommendations

Always respond in valid JSON format with these fields:
{
  "root_cause": "Clear explanation of the primary cause",
  "severity": "critical|high|medium|low",
  "confidence": 0.0-1.0,
  "impact_assessment": "Description of user/business impact",
  "contributing_factors": ["factor1", "factor2"],
  "timeline": [{"time": "HH:MM", "event": "description"}],
  "recommendations": ["action1", "action2"]
}"""
    
    def _create_rca_prompt(self, incident_id: str, context: str) -> str:
        """
        Create the RCA analysis prompt.
        """
        return f"""Analyze the following incident and provide root cause analysis.

**Incident ID**: {incident_id}
**Timestamp**: {datetime.utcnow().isoformat()}

{context}

Provide a comprehensive root cause analysis in JSON format."""
    
    def _prepare_context(
        self,
        metrics: Dict[str, Any],
        logs: List[str],
        traces: Optional[List[Dict]],
        similar_incidents: Optional[List[Dict]]
    ) -> str:
        """
        Prepare formatted context for the LLM.
        """
        context_parts = []
        
        # Add metrics
        context_parts.append("## METRICS")
        context_parts.append("```json")
        context_parts.append(json.dumps(metrics, indent=2))
        context_parts.append("```")
        
        # Add logs (limit to most relevant)
        context_parts.append("\n## RECENT LOGS")
        context_parts.append("```")
        # Take last 50 log lines to avoid token limit
        for log in logs[-50:]:
            context_parts.append(log)
        context_parts.append("```")
        
        # Add traces if available
        if traces:
            context_parts.append("\n## DISTRIBUTED TRACES")
            context_parts.append("```json")
            context_parts.append(json.dumps(traces[:10], indent=2))
            context_parts.append("```")
        
        # Add similar incidents for context
        if similar_incidents:
            context_parts.append("\n## SIMILAR PAST INCIDENTS")
            for inc in similar_incidents[:3]:
                context_parts.append(f"- **{inc.get('incident_id')}**: {inc.get('root_cause')}")
        
        return "\n".join(context_parts)
    
    async def process_chat_query(self, query: str, context: str) -> Dict[str, Any]:
        """
        Process natural language queries from ChatOps.
        """
        
        prompt = f"""You are a helpful DevOps assistant. Answer the following query about the {context} environment.

Query: {query}

Provide a helpful response with relevant metrics, visualizations suggestions, and actionable insights.
Respond in JSON format with fields: answer, metrics (dict), charts (list of chart configs)."""

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful DevOps and SRE assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_rca():
        agent = RCAAgent()
        
        test_metrics = {
            "cpu_usage_percent": 95.5,
            "memory_usage_percent": 87.2,
            "response_time_ms": 3500,
            "error_rate": 0.12
        }
        
        test_logs = [
            "2024-01-21 14:30:01 ERROR OutOfMemoryError: Java heap space",
            "2024-01-21 14:30:02 WARN Connection pool exhausted",
            "2024-01-21 14:30:03 ERROR Failed to allocate memory for order processing",
            "2024-01-21 14:30:05 INFO Attempting garbage collection",
            "2024-01-21 14:30:10 ERROR GC overhead limit exceeded"
        ]
        
        result = await agent.analyze(
            incident_id="INC-2024-001",
            metrics=test_metrics,
            logs=test_logs
        )
        
        print(json.dumps(result, indent=2))
    
    # asyncio.run(test_rca())