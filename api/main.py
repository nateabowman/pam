"""
FastAPI application for World P.A.M.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from api.routes import scenarios, signals
from api.auth import verify_api_key
from health import get_health
import os

app = FastAPI(
    title="World P.A.M. API",
    description="Predictive Analytic Machine for Geopolitical Scenarios",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scenarios.router, prefix="/api/v1", tags=["scenarios"])
app.include_router(signals.router, prefix="/api/v1", tags=["signals"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "World P.A.M. API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return get_health()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple web dashboard."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>World P.A.M. Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .scenario-card {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .probability {
                font-size: 24px;
                font-weight: bold;
                color: #e74c3c;
            }
            button {
                background: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
            }
            button:hover {
                background: #2980b9;
            }
            input {
                padding: 8px;
                margin: 5px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>World P.A.M. Dashboard</h1>
            <p>Predictive Analytic Machine for Geopolitical Scenarios</p>
        </div>
        
        <div>
            <h2>Evaluate Scenario</h2>
            <input type="text" id="scenario" placeholder="Scenario name" />
            <input type="text" id="country" placeholder="Country (optional)" />
            <input type="number" id="simulate" placeholder="Monte Carlo runs" value="0" />
            <button onclick="evaluateScenario()">Evaluate</button>
        </div>
        
        <div id="results"></div>
        
        <script>
            const API_KEY = prompt("Enter API Key:") || "";
            
            async function evaluateScenario() {
                const scenario = document.getElementById('scenario').value;
                const country = document.getElementById('country').value;
                const simulate = parseInt(document.getElementById('simulate').value) || 0;
                
                if (!scenario) {
                    alert("Please enter a scenario name");
                    return;
                }
                
                const url = `/api/v1/evaluate/${scenario}?simulate=${simulate}` + 
                    (country ? `&country=${encodeURIComponent(country)}` : '');
                
                try {
                    const response = await fetch(url, {
                        headers: {
                            'X-API-Key': API_KEY
                        }
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    const data = await response.json();
                    displayResult(data);
                } catch (error) {
                    alert("Error: " + error.message);
                }
            }
            
            function displayResult(data) {
                const resultsDiv = document.getElementById('results');
                const prob = (data.probability * 100).toFixed(1);
                
                let html = `<div class="scenario-card">
                    <h3>${data.scenario}</h3>
                    <div class="probability">${prob}%</div>
                `;
                
                if (data.monte_carlo) {
                    html += `<p>Monte Carlo: ${(data.monte_carlo.mean * 100).toFixed(1)}% 
                        (${(data.monte_carlo.confidence_interval.low * 100).toFixed(1)}% - 
                        ${(data.monte_carlo.confidence_interval.high * 100).toFixed(1)}%)</p>`;
                }
                
                html += `<h4>Signals:</h4><ul>`;
                for (const signal of data.signals) {
                    html += `<li>${signal.name}: ${signal.value.toFixed(3)} (weight: ${signal.weight})</li>`;
                }
                html += `</ul></div>`;
                
                resultsDiv.innerHTML = html;
            }
        </script>
    </body>
    </html>
    """
    return html

