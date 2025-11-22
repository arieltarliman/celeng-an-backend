import os
import time
from typing import List, Annotated, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import Supabase (Database) and Gemini (AI) logic
from database import get_user_client, supabase 
from llm_service import ask_gemini

load_dotenv()

app = FastAPI(title="Celeng-an Backend")

# 1. CORS - Allow your frontend to talk to this backend
origins = ["*"] # We allow all for now to make testing easier
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
    Extracts the Bearer Token from the header and creates a 
    user-specific Supabase client.
    """
    if not authorization:
        # Return public client (will fail RLS if trying to save)
        return supabase 
    try:
        token = authorization.replace("Bearer ", "")
        return get_user_client(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")

# 3. DATA MODELS
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
    # Optional: We might not have the image URL yet if we haven't uploaded it
    image_url: Optional[str] = None 

# 4. ENDPOINTS

@app.get("/")
def read_root():
    return {"status": "API is running", "ai_model": "Gemini Flash"}

# --- SCANNER (Read Only) ---
@app.post("/scan", response_model=ScanResult)
async def scan_receipt(
    file: UploadFile = File(...), 
    user_db = Depends(get_current_user_db)
):
    """
    Reads an image and returns JSON. Does NOT save to database.
    """
    # Validate File Type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP images allowed")

    # Read file
    content = await file.read()

    # Send to Gemini
    ai_result = ask_gemini(content, mime_type=file.content_type)

    if "error" in ai_result:
        raise HTTPException(status_code=500, detail=ai_result["details"])

    return ai_result

# --- SAVER (Write to DB) ---
@app.post("/save")
async def save_transaction(
    data: ScanResult, 
    user_db = Depends(get_current_user_db)
):
    """
    Receives the JSON data (after user review) and saves it to Supabase.
    """
    # A. Verify User is Logged In
    try:
        user_resp = user_db.auth.get_user()
        user_id = user_resp.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="You must be logged in to save data.")

    # B. Prepare Receipt Header
    receipt_payload = {
        "user_id": user_id,
        "merchant_name": data.merchant,
        "receipt_date": data.date,
        "total_amount": data.total_amount,
        "item_count": len(data.items),
        "image_url": data.image_url 
    }

    # C. Insert Header into 'receipts' table
    try:
        # .execute() is required to actually run the query
        response = user_db.table("receipts").insert(receipt_payload).execute()
        # Get the ID of the newly created receipt
        if not response.data:
            raise Exception("Database returned no data")
        
        new_receipt_id = response.data[0]['id']
        
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save receipt header: {str(e)}")

    # D. Prepare Items
    if data.items:
        items_payload = []
        for item in data.items:
            items_payload.append({
                "receipt_id": new_receipt_id,
                "item_name": item.name,
                "qty": item.qty,
                "unit_price": item.price,
                "line_total": item.total
            })

        # E. Insert Items into 'receipt_items' table
        try:
            user_db.table("receipt_items").insert(items_payload).execute()
        except Exception as e:
            print(f"Item Save Error: {e}")
            # We don't fail the whole request if items fail, but we log it
            # Ideally, you might want to delete the header if items fail (transactional)

    return {
        "status": "success", 
        "message": "Transaction saved successfully", 
        "receipt_id": new_receipt_id
    }