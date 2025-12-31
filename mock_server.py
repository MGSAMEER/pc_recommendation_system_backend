#!/usr/bin/env python3
"""
Simple mock backend server for PC Recommendation System
This provides basic API endpoints using Python's built-in HTTP server
"""
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class PCRecommendationHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        self.send_response(200)
        self.send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        if path == '/':
            response = {
                "message": "PC Recommendation System API",
                "status": "running",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        elif path == '/api/v1/health':
            response = {
                "status": "healthy",
                "service": "pc-recommendation-api",
                "timestamp": datetime.now().isoformat()
            }
        elif path == '/api/v1/test':
            response = {
                "message": "Test endpoint working",
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
        elif path == '/api/v1/components':
            response = {
                "components": [
                    {
                        "id": "cpu_001",
                        "name": "Intel Core i5-12400F",
                        "type": "cpu",
                        "price": 180,
                        "performance_score": 85
                    },
                    {
                        "id": "gpu_001", 
                        "name": "NVIDIA RTX 3060",
                        "type": "gpu",
                        "price": 320,
                        "performance_score": 90
                    }
                ],
                "total": 2
            }
        else:
            response = {
                "error": "Endpoint not found",
                "path": path,
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except json.JSONDecodeError:
            data = {}
        
        self.send_response(200)
        self.send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/v1/recommendations':
            # Mock recommendation response
            response = {
                "recommendations": [
                    {
                        "id": "rec_001",
                        "name": "Gaming Build",
                        "purpose": data.get('purpose', 'gaming'),
                        "budget_range": data.get('budget', {'min': 800, 'max': 1500}),
                        "components": [
                            {"type": "cpu", "name": "AMD Ryzen 5 5600X", "price": 200},
                            {"type": "gpu", "name": "NVIDIA RTX 3060", "price": 320},
                            {"type": "ram", "name": "16GB DDR4", "price": 80},
                            {"type": "storage", "name": "500GB SSD", "price": 60}
                        ],
                        "total_price": 660,
                        "confidence_score": 0.85,
                        "explanation": "This build provides excellent gaming performance within your budget range."
                    },
                    {
                        "id": "rec_002", 
                        "name": "Budget Gaming Build",
                        "purpose": data.get('purpose', 'gaming'),
                        "budget_range": data.get('budget', {'min': 800, 'max': 1500}),
                        "components": [
                            {"type": "cpu", "name": "Intel Core i5-12400F", "price": 180},
                            {"type": "gpu", "name": "NVIDIA GTX 1660 Super", "price": 250},
                            {"type": "ram", "name": "16GB DDR4", "price": 80},
                            {"type": "storage", "name": "256GB SSD", "price": 40}
                        ],
                        "total_price": 550,
                        "confidence_score": 0.78,
                        "explanation": "A cost-effective gaming build that still delivers solid performance."
                    }
                ],
                "request_data": data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "error": "POST endpoint not found",
                "path": path,
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom log message format"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=8000):
    """Run the mock backend server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, PCRecommendationHandler)
    print(f"Mock PC Recommendation API Server running on http://localhost:{port}")
    print("Available endpoints:")
    print("  GET  / - API info")
    print("  GET  /api/v1/health - Health check")
    print("  GET  /api/v1/test - Test endpoint")
    print("  GET  /api/v1/components - Mock components")
    print("  POST /api/v1/recommendations - Get recommendations")
    print("\nPress Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()