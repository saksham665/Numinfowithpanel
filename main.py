from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional

app = FastAPI(title="Combined API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keys - आप easily change कर सकते हैं
KEYS = {
    "NUM": "trialkey",      # Mobile number API key
    "FAMILY": "trialkey",         # Family info API key  
    "VEHICLE": "trialkey" # Vehicle API key
}

@app.get("/")
async def root():
    return {"message": "Combined API is running", "credit": "@Useful_thingsss"}

@app.get("/fetch")
async def fetch_data(
    key: str = Query(..., description="API Key"),
    num: Optional[str] = Query(None, description="Mobile number"),
    family: Optional[str] = Query(None, description="Aadhaar number"), 
    vehicle: Optional[str] = Query(None, description="Vehicle number")
):
    try:
        result = {}
        
        # Handle mobile number lookup
        if num:
            if key != KEYS["NUM"]:
                raise HTTPException(status_code=401, detail="Invalid key for number API")
            result = await handle_number_lookup(num)
        
        # Handle family info lookup
        elif family:
            if key != KEYS["FAMILY"]:
                raise HTTPException(status_code=401, detail="Invalid key for family API")
            result = await handle_family_lookup(family)
        
        # Handle vehicle info lookup  
        elif vehicle:
            if key != KEYS["VEHICLE"]:
                raise HTTPException(status_code=401, detail="Invalid key for vehicle API")
            result = await handle_vehicle_lookup(vehicle)
        
        else:
            raise HTTPException(status_code=400, detail="Please provide num, family or vehicle parameter")
        
        # Add credit
        result["credit"] = "@Useful_thingsss"
        
        return JSONResponse(content=result, media_type="application/json")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_number_lookup(mobile: str):
    url = f"https://seller-ki-mkc.taitanx.workers.dev/?mobile={mobile}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    
    # Remove credit and developer fields
    filtered_data = {k: v for k, v in data.items() if k not in ["credit", "developer"]}
    return filtered_data

async def handle_family_lookup(aadhaar: str):
    url = f"https://family-info-theta.vercel.app/fetch?key={KEYS['FAMILY']}&aadhaar={aadhaar}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    
    # Remove credit and developer fields
    filtered_data = {k: v for k, v in data.items() if k not in ["credit", "developer"]}
    return filtered_data

async def handle_vehicle_lookup(vehicle_no: str):
    url = f"https://anmol-vehicle-info.vercel.app/vehicle_info?vehicle_no={vehicle_no}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    
    # Remove credit and developer fields
    filtered_data = {k: v for k, v in data.items() if k not in ["credit", "developer"]}
    return filtered_data

# Vercel के लिए handler
@app.get("/api/fetch")
async def api_fetch(
    key: str = Query(..., description="API Key"),
    num: Optional[str] = Query(None, description="Mobile number"),
    family: Optional[str] = Query(None, description="Aadhaar number"), 
    vehicle: Optional[str] = Query(None, description="Vehicle number")
):
    return await fetch_data(key, num, family, vehicle)
