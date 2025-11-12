const fetch = require('node-fetch');

// Keys - आप easily change कर सकते हैं
const KEYS = {
  NUM: 'trialkey_num',      // Mobile number API key
  FAMILY: 'PRINCE',         // Family info API key  
  VEHICLE: 'trialkey_vehicle' // Vehicle API key
};

// Main API handler
module.exports = async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle OPTIONS request for CORS
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  const { key, num, family, vehicle } = req.query;
  
  try {
    // Validate key
    if (!key) {
      return res.status(400).json({ 
        error: 'Key parameter is required',
        credit: '@Useful_thingsss'
      });
    }
    
    let result;
    
    // Handle mobile number lookup
    if (num) {
      if (key !== KEYS.NUM) {
        return res.status(401).json({ 
          error: 'Invalid key for number API',
          credit: '@Useful_thingsss'
        });
      }
      result = await handleNumberLookup(num);
    }
    // Handle family info lookup
    else if (family) {
      if (key !== KEYS.FAMILY) {
        return res.status(401).json({ 
          error: 'Invalid key for family API', 
          credit: '@Useful_thingsss'
        });
      }
      result = await handleFamilyLookup(family);
    }
    // Handle vehicle info lookup
    else if (vehicle) {
      if (key !== KEYS.VEHICLE) {
        return res.status(401).json({ 
          error: 'Invalid key for vehicle API',
          credit: '@Useful_thingsss'
        });
      }
      result = await handleVehicleLookup(vehicle);
    }
    else {
      return res.status(400).json({ 
        error: 'Please provide num, family or vehicle parameter',
        credit: '@Useful_thingsss'
      });
    }
    
    // Add credit and return response
    result.credit = '@Useful_thingsss';
    res.setHeader('Content-Type', 'application/json');
    return res.status(200).send(JSON.stringify(result));
    
  } catch (error) {
    console.error('API Error:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      credit: '@Useful_thingsss'
    });
  }
};

// Mobile number lookup handler
async function handleNumberLookup(mobile) {
  const url = `https://seller-ki-mkc.taitanx.workers.dev/?mobile=${encodeURIComponent(mobile)}`;
  const response = await fetch(url);
  const data = await response.json();
  
  // Remove credit and developer fields
  const { credit, developer, ...filteredData } = data;
  return filteredData;
}

// Family info lookup handler  
async function handleFamilyLookup(aadhaar) {
  const url = `https://family-info-theta.vercel.app/fetch?key=${KEYS.FAMILY}&aadhaar=${encodeURIComponent(aadhaar)}`;
  const response = await fetch(url);
  const data = await response.json();
  
  // Remove credit and developer fields
  const { credit, developer, ...filteredData } = data;
  return filteredData;
}

// Vehicle info lookup handler
async function handleVehicleLookup(vehicleNo) {
  const url = `https://anmol-vehicle-info.vercel.app/vehicle_info?vehicle_no=${encodeURIComponent(vehicleNo)}`;
  const response = await fetch(url);
  const data = await response.json();
  
  // Remove credit and developer fields
  const { credit, developer, ...filteredData } = data;
  return filteredData;
                                    }
