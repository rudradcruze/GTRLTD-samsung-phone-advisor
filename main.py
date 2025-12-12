"""
Samsung Phone Advisor - FastAPI Server
Unified RAG + Multi-Agent System for Samsung phone recommendations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from database import init_db, SessionLocal, Phone
from rag_module import get_rag_module
from agents import get_agent_system

# Initialize FastAPI app
app = FastAPI(
    title="Samsung Phone Advisor",
    description="A smart assistant for Samsung phone recommendations using RAG + Multi-Agent System",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


class PhoneResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    id: int
    model_name: str
    release_date: Optional[str]
    display: Optional[str]
    battery: Optional[str]
    camera: Optional[str]
    ram: Optional[str]
    storage: Optional[str]
    price: Optional[str]
    chipset: Optional[str]
    os: Optional[str]


class HealthResponse(BaseModel):
    status: str
    database: str
    phone_count: int


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Samsung Phone Advisor API started!")


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Samsung Phone Advisor API",
        "version": "1.0.0",
        "description": "Ask questions about Samsung phones",
        "endpoints": {
            "/ask": "POST - Ask a question about Samsung phones",
            "/phones": "GET - List all phones in database",
            "/phones/{model_name}": "GET - Get specific phone details",
            "/health": "GET - Check API health status"
        }
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Main endpoint for asking questions about Samsung phones

    Supports:
    - Direct specs: "What are the specs of Samsung Galaxy S23 Ultra?"
    - Comparisons: "Compare Galaxy S23 Ultra and S22 Ultra for photography"
    - Recommendations: "Which Samsung phone has the best battery under $1000?"
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(status_code=400, detail="Question must be at least 3 characters")

    try:
        # Get the multi-agent system
        agent_system = get_agent_system()

        # Process the query through the multi-agent pipeline
        answer = agent_system.process_query(request.question)

        return AnswerResponse(answer=answer)

    except Exception as e:
        print(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing your question: {str(e)}")


@app.get("/phones", response_model=List[PhoneResponse])
async def get_all_phones():
    """Get all Samsung phones in the database"""
    db = SessionLocal()
    try:
        phones = db.query(Phone).all()
        return [PhoneResponse(
            id=p.id,
            model_name=p.model_name,
            release_date=p.release_date,
            display=p.display,
            battery=p.battery,
            camera=p.camera,
            ram=p.ram,
            storage=p.storage,
            price=p.price,
            chipset=p.chipset,
            os=p.os
        ) for p in phones]
    finally:
        db.close()


@app.get("/phones/{model_name}", response_model=PhoneResponse)
async def get_phone_by_name(model_name: str):
    """Get a specific phone by model name"""
    rag = get_rag_module()
    phone = rag.get_phone_by_name(model_name)

    if not phone:
        raise HTTPException(status_code=404, detail=f"Phone '{model_name}' not found")

    return PhoneResponse(
        id=phone.id,
        model_name=phone.model_name,
        release_date=phone.release_date,
        display=phone.display,
        battery=phone.battery,
        camera=phone.camera,
        ram=phone.ram,
        storage=phone.storage,
        price=phone.price,
        chipset=phone.chipset,
        os=phone.os
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and database status"""
    db = SessionLocal()
    try:
        phone_count = db.query(Phone).count()
        return HealthResponse(
            status="healthy",
            database="connected",
            phone_count=phone_count
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database=f"error: {str(e)}",
            phone_count=0
        )
    finally:
        db.close()


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
