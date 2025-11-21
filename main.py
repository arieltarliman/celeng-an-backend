import os
import time
from typing import List, Annotated

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from database import get_user_client, supabase 

app = FastAPI(title="Celeng-an Backend")

origins = [
    "http://localhost:3000",                      # Local Frontend
    "https://celeng-an.vercel.app",               # Your future Vercel URL (Update this later!)
    "https://your-production-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. AUTHENTICATION DEPENDENCY
async def get_current_user_db(authorization: Annotated[str | None, Header()] = None):
    """
    Extracts the 'Bearer <token>' from the header.
    Returns a Supabase Client authenticated as that specific user.
    """
    if not authorization:
        # Allow access for now if you are just testing with Swagger UI without a token
        # In production, change this to: raise HTTPException(status_code=401)
        print("Warning: No Token provided. Using anonymous client.")
        return supabase 

    try:
        token = authorization.replace("Bearer ", "")
        # This creates a client specifically for this user (RLS safe)
        return get_user_client(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")

# 3. DATA MODELS (Pydantic)
class ReceiptItem(BaseModel):
    name: str
    qty: int
    price: int
    total: int

class ScanResult(BaseModel):
    merchant: str
    date: str
    items: List[ReceiptItem]
    total_amount: int

# 4. ENDPOINTS

@app.get("/")
def read_root():
    return {"status": "API is running on Koyeb", "service": "Celeng-an Backend"}

@app.post("/scan/mock", response_model=ScanResult)
async def mock_ocr_scan(
    file: UploadFile = File(...), 
    user_db = Depends(get_current_user_db) # This ensures only logged-in users can scan
):
    """
    [MOCK] Use this while waiting for the AI team.
    It simulates scanning an Indomaret receipt.
    """
    # Simulate processing time (AI is slow!)
    time.sleep(2) 
    
    # NOTE: In the real version, we would use 'user_db' here to:
    # 1. Upload the 'file' to Supabase Storage bucket 'receipts'
    # 2. Insert the result into the 'receipts' table
    
    return {
        "merchant": "INDOMARET POINT",
        "date": "2025-11-21",
        "items": [
            {"name": "Aqua 600ml", "qty": 2, "price": 3500, "total": 7000},
            {"name": "Sari Roti", "qty": 1, "price": 12000, "total": 12000},
            {"name": "Plastik", "qty": 1, "price": 500, "total": 500}
        ],
        "total_amount": 19500
    }