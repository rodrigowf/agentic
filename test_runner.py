#!/usr/bin/env python3
"""
Simple test script to verify the backend and frontend are working properly.
"""

import subprocess
import time
import sys
import os

def start_backend():
    """Start the backend server"""
    print("🚀 Starting backend server...")
    backend_process = subprocess.Popen(
        ["uvicorn", "main:app", "--reload", "--reload-exclude", "workspace"],
        cwd="./backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait a bit for the server to start
    time.sleep(3)
    
    # Check if the process is still running
    if backend_process.poll() is None:
        print("✅ Backend started successfully on http://localhost:8000")
        return backend_process
    else:
        print("❌ Backend failed to start")
        output, _ = backend_process.communicate()
        print(f"Error output: {output}")
        return None

def start_frontend():
    """Start the frontend development server"""
    print("🎨 Starting frontend server...")
    frontend_process = subprocess.Popen(
        ["npm", "start"],
        cwd="./frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait a bit for the server to start
    time.sleep(5)
    
    # Check if the process is still running
    if frontend_process.poll() is None:
        print("✅ Frontend started successfully on http://localhost:3000")
        return frontend_process
    else:
        print("❌ Frontend failed to start")
        output, _ = frontend_process.communicate()
        print(f"Error output: {output}")
        return None

def main():
    """Main test function"""
    print("🧪 Testing Agentic Application")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("backend") or not os.path.exists("frontend"):
        print("❌ Please run this script from the agentic root directory")
        sys.exit(1)
    
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        backend_process = start_backend()
        if not backend_process:
            sys.exit(1)
        
        # Start frontend
        frontend_process = start_frontend()
        if not frontend_process:
            sys.exit(1)
        
        print("\n🎉 Both servers are running!")
        print("📖 Instructions:")
        print("1. Open http://localhost:3000 in your browser")
        print("2. Try running the 'Researcher' agent")
        print("3. Test the Voice Assistant at http://localhost:3000/voice")
        print("4. Press Ctrl+C to stop both servers")
        
        # Keep the script running until interrupted
        while True:
            time.sleep(1)
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("❌ Backend process died")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend process died")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up processes
        for process, name in [(backend_process, "backend"), (frontend_process, "frontend")]:
            if process and process.poll() is None:
                print(f"🔄 Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} stopped")
                except subprocess.TimeoutExpired:
                    print(f"⚠️  Force killing {name}...")
                    process.kill()

if __name__ == "__main__":
    main()
