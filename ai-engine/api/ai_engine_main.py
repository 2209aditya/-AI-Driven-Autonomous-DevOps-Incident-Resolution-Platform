# ai-engine/api/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import os

from llm.rca_agent import RCAAgent
from llm.fix_generator import FixGenerator
from anomaly_detection.predict import AnomalyPredictor
from vector_db.faiss_index import VectorSearch

app = FastAPI(
    title="AI-Driven DevOps Platform",
    description="Autonomous incident resolution and AIOps system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI components
rca_agent = RCAAgent()
fix_generator = FixGenerator()
anomaly_predictor = AnomalyPredictor()
vector_search = VectorSearch()


# Request/Response Models
class IncidentAnalysisRequest(BaseModel):
    incident_id: str
    timestamp: datetime
    service_name: str
    metrics: Dict[str, Any]
    logs: List[str]
    traces: Optional[List[Dict]] = None
    severity: Optional[str] = "medium"


class IncidentAnalysisResponse(BaseModel):
    incident_id: str
    root_cause: str
    severity: str
    confidence: float
    impact_assessment: str
    recommended_fix: Dict[str, Any]
    generated_code: str
    similar_incidents: List[Dict]
    timeline: List[Dict]


class ChatQueryRequest(BaseModel):
    query: str
    context: Optional[str] = "production"
    user_id: Optional[str] = None


class AnomalyPredictionResponse(BaseModel):
    service_name: str
    timestamp: datetime
    is_anomaly: bool
    confidence: float
    anomaly_score: float
    predicted_metrics: Dict[str, float]
    recommendation: str


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "rca_agent": "operational",
            "anomaly_detector": "operational",
            "vector_db": "operational"
        }
    }


# Main incident analysis endpoint
@app.post("/api/v1/incidents/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incident(request: IncidentAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Analyze an incident using GenAI and provide root cause analysis
    with auto-remediation recommendations.
    """
    try:
        # Step 1: Find similar past incidents
        similar_incidents = await vector_search.find_similar_incidents(
            service=request.service_name,
            logs=request.logs[:10],  # Use first 10 log lines for embedding
            top_k=3
        )
        
        # Step 2: Perform RCA using LLM
        rca_result = await rca_agent.analyze(
            incident_id=request.incident_id,
            metrics=request.metrics,
            logs=request.logs,
            traces=request.traces,
            similar_incidents=similar_incidents
        )
        
        # Step 3: Generate fix code
        fix_code = await fix_generator.generate_fix(
            root_cause=rca_result["root_cause"],
            service_name=request.service_name,
            severity=rca_result["severity"]
        )
        
        # Step 4: Create incident timeline
        timeline = [
            {"time": request.timestamp.isoformat(), "event": "Incident detected"},
            {"time": datetime.utcnow().isoformat(), "event": "RCA completed"},
            {"time": datetime.utcnow().isoformat(), "event": "Fix generated"}
        ]
        
        # Background: Store incident in vector DB for future reference
        background_tasks.add_task(
            vector_search.store_incident,
            incident_id=request.incident_id,
            data={
                "service": request.service_name,
                "root_cause": rca_result["root_cause"],
                "logs": request.logs
            }
        )
        
        return IncidentAnalysisResponse(
            incident_id=request.incident_id,
            root_cause=rca_result["root_cause"],
            severity=rca_result["severity"],
            confidence=rca_result["confidence"],
            impact_assessment=rca_result["impact"],
            recommended_fix=fix_code["fix_details"],
            generated_code=fix_code["code"],
            similar_incidents=similar_incidents,
            timeline=timeline
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# Anomaly prediction endpoint
@app.get("/api/v1/predict/anomalies", response_model=List[AnomalyPredictionResponse])
async def predict_anomalies(service: str, window: str = "1h"):
    """
    Predict anomalies for a service using ML models.
    """
    try:
        predictions = await anomaly_predictor.predict(
            service_name=service,
            time_window=window
        )
        
        results = []
        for pred in predictions:
            results.append(AnomalyPredictionResponse(
                service_name=service,
                timestamp=pred["timestamp"],
                is_anomaly=pred["is_anomaly"],
                confidence=pred["confidence"],
                anomaly_score=pred["score"],
                predicted_metrics=pred["metrics"],
                recommendation=pred["recommendation"]
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ChatOps query endpoint
@app.post("/api/v1/chat/query")
async def chat_query(request: ChatQueryRequest):
    """
    Process natural language queries about infrastructure.
    """
    try:
        # Use LLM to understand the query and generate appropriate response
        response = await rca_agent.process_chat_query(
            query=request.query,
            context=request.context
        )
        
        return {
            "query": request.query,
            "response": response["answer"],
            "data": response.get("metrics", {}),
            "visualizations": response.get("charts", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Auto-remediation endpoint
@app.post("/api/v1/remediation/execute")
async def execute_remediation(
    incident_id: str,
    fix_type: str,
    auto_approve: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Execute auto-remediation for an incident.
    """
    try:
        if auto_approve:
            # Execute immediately
            result = await fix_generator.apply_fix(
                incident_id=incident_id,
                fix_type=fix_type
            )
            return {
                "status": "applied",
                "incident_id": incident_id,
                "result": result
            }
        else:
            # Create PR for manual approval
            pr_url = await fix_generator.create_pull_request(
                incident_id=incident_id,
                fix_type=fix_type
            )
            return {
                "status": "pending_approval",
                "incident_id": incident_id,
                "pr_url": pr_url
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")


# Metrics endpoint for Prometheus scraping
@app.get("/metrics")
async def metrics():
    """
    Expose metrics for Prometheus.
    """
    # In production, use prometheus_client library
    return {
        "aiops_incidents_total": 150,
        "aiops_remediation_success_rate": 0.87,
        "aiops_mttr_seconds": 240,
        "aiops_anomaly_detection_precision": 0.92
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )