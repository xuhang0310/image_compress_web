#!/usr/bin/env python3
import os
import sys
import argparse
import webbrowser
import uvicorn
import socket
import warnings
import threading
import time

# Filter out the specific warning from torch.amp.autocast_mode
warnings.filterwarnings("ignore", message="User provided device_type of 'cuda', but CUDA is not available")

from api.deps import set_lama_config

def get_free_port(host="127.0.0.1", port=8080):
    """Try to find a free port starting from the given port."""
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            port += 1
            if port > 65535:
                raise RuntimeError("No free ports available")

def main():
    parser = argparse.ArgumentParser(description="Image Compress & Watermark Removal Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", default=8080, type=int, help="Port to bind (default: 8080)")
    parser.add_argument("--model", default="lama", help="Inpainting model name (default: lama)")
    parser.add_argument("--device", default=None, help="Device to use (cuda, mps, cpu). Default: auto-detect")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (auto-reload)")
    parser.add_argument("--no-gui", action="store_true", help="Do not open browser automatically")
    
    args = parser.parse_args()

    # Ensure we are in the script's directory so imports work correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.getcwd())

    # Set global configuration for Lama model
    set_lama_config(args.model, args.device)

    # Check if port is available
    final_port = get_free_port(args.host, args.port)
    if final_port != args.port:
        print(f"Warning: Port {args.port} is in use. Using {final_port} instead.")
    
    server_url = f"http://{args.host}:{final_port}"
    print(f"\n{'='*50}")
    print(f"🚀 Starting Image Compress & Watermark Removal Server")
    print(f"🌍 URL: {server_url}")
    print(f"🧠 Model: {args.model}")
    print(f"💻 Device: {args.device if args.device else 'Auto-detect'}")
    print(f"{'='*50}\n")

    # Function to open browser after a delay
    def open_browser_delayed():
        time.sleep(1.5)  # Wait for server to start
        try:
            webbrowser.open(server_url)
        except Exception as e:
            print(f"Failed to open browser: {e}")

    # Open browser in a separate thread after server starts
    if not args.no_gui:
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Run the application
    # Use "backend:app" string to enable reload if debug is True
    try:
        uvicorn.run(
            "backend:app",
            host=args.host,
            port=final_port,
            reload=args.debug,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")

if __name__ == "__main__":
    main()
