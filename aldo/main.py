from fastapi import FastAPI, UploadFile, File, HTTPException
from app.llm_service import ask_gemini

app = FastAPI()

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        result = ask_gemini(image_bytes)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
