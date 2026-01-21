import pytest
from unittest.mock import Mock, patch
from llm.rca_agent import RCAAgent

@pytest.fixture
def rca_agent():
    return RCAAgent()

@pytest.mark.asyncio
async def test_analyze_incident(rca_agent):
    """Test RCA analysis."""
    metrics = {"cpu_usage_percent": 95.5}
    logs = ["ERROR: Out of memory"]
    
    # Mock the OpenAI call
    with patch.object(rca_agent.client.chat.completions, 'create') as mock_create:
        mock_create.return_value.choices[0].message.content = '{"root_cause": "Memory leak", "severity": "high", "confidence": 0.9}'
        
        result = await rca_agent.analyze(
            incident_id="INC-001",
            metrics=metrics,
            logs=logs
        )
        
        assert result["root_cause"] == "Memory leak"
        assert result["severity"] == "high"
        assert result["confidence"] == 0.9
