// API client with dynamic configuration
let API_BASE = "http://localhost:8000";

// Load configuration at runtime
const loadConfig = async () => {
  try {
    const response = await fetch('/config.json');
    const config = await response.json();
    API_BASE = config.apiBaseUrl || API_BASE;
  } catch (error) {
    console.warn('Could not load config, using default:', API_BASE);
  }
};

// Load config when module is imported
loadConfig();

// API client functions
export const apiClient = {
  // Process agricultural query
  async processQuery(query, userId = null, region = null, language = "auto") {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        user_id: userId,
        region,
        language,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Process query with Groq
  async processQueryWithGroq(query, userId = null, region = null, language = "auto") {
    const response = await fetch(`${API_BASE}/query/groq`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        user_id: userId,
        region,
        language,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Get graph data for visualization
  async getGraphData() {
    const response = await fetch(`${API_BASE}/graph`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Get 1-hop neighborhood for a node name
  async getGraphNeighbors(name, limit = 24) {
    const url = new URL(`${API_BASE}/graph/neighbors`);
    url.searchParams.append('name', name);
    url.searchParams.append('limit', String(limit));
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  },

  // Trigger manual updates
  async triggerUpdate(updateType = "all") {
    const response = await fetch(`${API_BASE}/update`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        update_type: updateType,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Get recent events
  async getRecentEvents() {
    const response = await fetch(`${API_BASE}/events`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Get system status
  async getSystemStatus() {
    const response = await fetch(`${API_BASE}/status`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Search entities
  async searchEntities(entityType, searchTerm = "") {
    const url = new URL(`${API_BASE}/search/${entityType}`);
    if (searchTerm) {
      url.searchParams.append("q", searchTerm);
    }
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Voice query endpoint
  async processVoiceQuery(audioBlob, language = "auto") {
    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.wav");
    formData.append("language", language);
    
    const response = await fetch(`${API_BASE}/voice-query`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Text-to-speech endpoint
  async textToSpeech(text, language = "en", voice = "alloy") {
    const response = await fetch(`${API_BASE}/text-to-speech`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        language,
        voice,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.blob();
  },

  // Fertilizer recommendation (ML-based)
  async getFertilizerRecommendation(params) {
    const response = await fetch(`${API_BASE}/fertilizer/recommendation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Search fertilizers
  async searchFertilizers(searchTerm = "") {
    const url = new URL(`${API_BASE}/fertilizer/search`);
    if (searchTerm) url.searchParams.append("search_term", searchTerm);
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  },

  // Get weather by GPS coordinates
  async getWeatherByGPS(latitude, longitude) {
    const response = await fetch(`${API_BASE}/live-data/weather/gps/${latitude}/${longitude}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
};

export default apiClient;