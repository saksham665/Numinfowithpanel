from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ORIGINAL API URLs with their FIXED keys - YE CHANGE NAHI HONGE
ORIGINAL_APIS = {
    "NUM": {
        "url": "https://seller-ki-mkc.taitanx.workers.dev/?mobile={query}",
        "original_key": None  # Isme koi key nahi hai
    },
    "FAMILY": {
        "url": "https://family-info-theta.vercel.app/fetch?key=PRINCE&aadhaar={query}",
        "original_key": "PRINCE"  # Yeh fixed hai
    },
    "VEHICLE": {
        "url": "https://anmol-vehicle-info.vercel.app/vehicle_info?vehicle_no={query}",
        "original_key": None  # Isme bhi koi key nahi hai
    }
}

# AAPKE NEW API KEYS - AAP INHE CHANGE KAR SAKTE HO
MY_KEYS = {
    "NUM": "trialkey",      # Mobile number API key - CHANGE KAR SAKTE HO
    "FAMILY": "trialkey",  # Family info API key - CHANGE KAR SAKTE HO  
    "VEHICLE": "trialkey" # Vehicle API key - CHANGE KAR SAKTE HO
}

@app.route('/')
def home():
    return jsonify({
        "message": "Combined API is running", 
        "credit": "@Useful_thingsss",
        "available_endpoints": {
            "mobile": "/api/fetch?key=YOUR_KEY&num=MOBILE_NUMBER",
            "family": "/api/fetch?key=YOUR_KEY&family=AADHAAR_NUMBER", 
            "vehicle": "/api/fetch?key=YOUR_KEY&vehicle=VEHICLE_NUMBER"
        }
    })

@app.route('/api/fetch')
def fetch_data():
    key = request.args.get('key')
    num = request.args.get('num')
    family = request.args.get('family')
    vehicle = request.args.get('vehicle')
    
    if not key:
        return jsonify({"error": "Key parameter is required", "credit": "@Useful_thingsss"}), 400
    
    try:
        # Handle mobile number lookup
        if num:
            if key != MY_KEYS["NUM"]:
                return jsonify({"error": "Invalid key for number API", "credit": "@Useful_thingsss"}), 401
            result = handle_number_lookup(num)
        
        # Handle family info lookup
        elif family:
            if key != MY_KEYS["FAMILY"]:
                return jsonify({"error": "Invalid key for family API", "credit": "@Useful_thingsss"}), 401
            result = handle_family_lookup(family)
        
        # Handle vehicle info lookup  
        elif vehicle:
            if key != MY_KEYS["VEHICLE"]:
                return jsonify({"error": "Invalid key for vehicle API", "credit": "@Useful_thingsss"}), 401
            result = handle_vehicle_lookup(vehicle)
        
        else:
            return jsonify({"error": "Please provide num, family or vehicle parameter", "credit": "@Useful_thingsss"}), 400
        
        # Add credit
        if isinstance(result, dict):
            result["credit"] = "@Useful_thingsss"
        else:
            result = {"data": result, "credit": "@Useful_thingsss"}
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal server error", "credit": "@Useful_thingsss"}), 500

def handle_number_lookup(mobile):
    """Original API: https://seller-ki-mkc.taitanx.workers.dev/?mobile="""
    url = ORIGINAL_APIS["NUM"]["url"].format(query=mobile)
    response = requests.get(url)
    data = response.json()
    
    # Remove credit and developer fields from original response
    return remove_unwanted_fields(data)

def handle_family_lookup(aadhaar):
    """Original API: https://family-info-theta.vercel.app/fetch?key=PRINCE&aadhaar="""
    url = ORIGINAL_APIS["FAMILY"]["url"].format(query=aadhaar)
    response = requests.get(url)
    data = response.json()
    
    # Remove credit and developer fields from original response
    return remove_unwanted_fields(data)

def handle_vehicle_lookup(vehicle_no):
    """Original API: https://anmol-vehicle-info.vercel.app/vehicle_info?vehicle_no="""
    url = ORIGINAL_APIS["VEHICLE"]["url"].format(query=vehicle_no)
    response = requests.get(url)
    data = response.json()
    
    # Remove credit and developer fields from original response
    return remove_unwanted_fields(data)

def remove_unwanted_fields(data):
    """Remove credit and developer fields from original API response"""
    if isinstance(data, dict):
        # Nested fields ko bhi check karein
        cleaned_data = {}
        for k, v in data.items():
            if k not in ["credit", "developer"]:
                if isinstance(v, dict):
                    cleaned_data[k] = remove_unwanted_fields(v)
                elif isinstance(v, list):
                    cleaned_data[k] = [remove_unwanted_fields(item) if isinstance(item, dict) else item for item in v]
                else:
                    cleaned_data[k] = v
        return cleaned_data
    return data

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({"status": "active", "credit": "@Useful_thingsss"})

if __name__ == '__main__':
    app.run(debug=True)
