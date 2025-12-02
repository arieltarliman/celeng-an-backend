import os
import time
import uuid
from typing import List, Annotated, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import Supabase and Gemini logic
from database import get_user_client, supabase 
from llm_service import ask_gemini

load_dotenv()

app = FastAPI(title="Celeng-an Backend")

# 1. CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. AUTHENTICATION DEPENDENCY
async def get_current_user_db(authorization: Annotated[str | None, Header()] = None):
    if not authorization:
        return supabase 
    try:
        token = authorization.replace("Bearer ", "")
        return get_user_client(token)
    except Exception:
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
    subtotal: int
    tax: int
    service: int
    total_amount: int
    image_url: Optional[str] = None 

# 4. ENDPOINTS

@app.get("/")
def read_root():
    return {"status": "API is running", "ai_model": "Gemini Flash"}

# --- NEW: UPLOAD ENDPOINT ---
@app.post("/upload")
async def upload_receipt_image(
    file: UploadFile = File(...),
    user_db = Depends(get_current_user_db)
):
    """
    Uploads the image to Supabase Storage ('receipts' bucket) 
    and returns the Public URL.
    """
    # 1. Validate User is Logged In (Required for Storage Policy)
    try:
        user = user_db.auth.get_user()
        user_id = user.user.id
    except:
        raise HTTPException(status_code=401, detail="Login required to upload images")

    # 2. Generate a Unique Filename
    # We use UUID to prevent filename collisions (e.g., two users uploading "image.jpg")
    file_ext = file.filename.split(".")[-1]
    file_path = f"{user_id}/{uuid.uuid4()}.{file_ext}"

    # 3. Read File Content
    file_content = await file.read()

    # 4. Upload to Supabase Storage
    try:
        # Ensure your bucket in Supabase is named 'receipts'
        user_db.storage.from_("receipts").upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage Upload Failed: {str(e)}")

    # 5. Get Public URL
    # Note: Ensure your 'receipts' bucket is set to PUBLIC in Supabase Dashboard
    public_url_response = user_db.storage.from_("receipts").get_public_url(file_path)
    
    return {"url": public_url_response}

# --- SCANNER ---
@app.post("/scan", response_model=ScanResult)
async def scan_receipt(
    file: UploadFile = File(...), 
    user_db = Depends(get_current_user_db)
):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP images allowed")

    content = await file.read()
    ai_result = ask_gemini(content, mime_type=file.content_type)

    if "error" in ai_result:
        raise HTTPException(status_code=500, detail=ai_result["details"])

    return ai_result

# --- SAVER ---
@app.post("/save")
async def save_transaction(
    data: ScanResult, 
    user_db = Depends(get_current_user_db)
):
    try:
        user_resp = user_db.auth.get_user()
        user_id = user_resp.user.id
    except:
        raise HTTPException(status_code=401, detail="You must be logged in to save data")

    receipt_payload = {
        "user_id": user_id,
        "merchant_name": data.merchant,
        "receipt_date": data.date,
        "subtotal": data.subtotal,
        "tax_amount": data.tax,
        "service_charge": data.service,
        "total_amount": data.total_amount,
        "item_count": len(data.items),
        "image_url": data.image_url
    }

    try:
        response = user_db.table("receipts").insert(receipt_payload).execute()
        new_receipt_id = response.data[0]['id']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save receipt: {str(e)}")

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
        try:
            user_db.table("receipt_items").insert(items_payload).execute()
        except Exception as e:
            print(f"Error saving items: {e}")

    return {
        "status": "success", 
        "message": "Transaction saved", 
        "receipt_id": new_receipt_id
    }