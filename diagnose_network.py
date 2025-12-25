#!/usr/bin/env python3
"""
Network accessibility diagnostic for PC Recommendation backend
"""
import socket
import subprocess
import sys
import os

def get_local_ip():
    """Get the local IP address"""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Could not determine local IP: {e}")
        return None

def check_port(port, host="127.0.0.1"):
    """Check if a port is open on the given host"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("=== PC RECOMMENDATION BACKEND NETWORK DIAGNOSTIC ===")
    print()

    # Get local IP
    local_ip = get_local_ip()
    if local_ip:
        print(f"Your local IP address: {local_ip}")
    else:
        print("Could not determine local IP address")
        print("Make sure you're connected to a network")
        return

    print()

    # Check server status
    print("Checking server status:")
    ports = [8000, 8002]

    for port in ports:
        localhost_running = check_port(port, "127.0.0.1")
        network_running = check_port(port, local_ip) if local_ip else False

        print(f"Port {port}:")
        print(f"  Localhost (127.0.0.1): {'RUNNING' if localhost_running else 'NOT RUNNING'}")
        print(f"  Network ({local_ip}): {'ACCESSIBLE' if network_running else 'NOT ACCESSIBLE'}")

        if localhost_running and not network_running:
            print("  WARNING: Server running locally but not accessible from network!")
            print("  This indicates a firewall or binding issue.")
        elif not localhost_running:
            print("  Server not running on this port.")

    print()

    # Firewall check
    print("Firewall check:")
    try:
        # Check if we're on Windows
        if os.name == 'nt':
            result = subprocess.run(['netsh', 'advfirewall', 'show', 'currentprofile'],
                                  capture_output=True, text=True, timeout=5)
            if 'State ON' in result.stdout:
                print("Windows Firewall: ENABLED")

                # Check specific ports
                for port in ports:
                    rule_check = subprocess.run(
                        ['netsh', 'advfirewall', 'firewall', 'show', 'rule', f'name=PC Backend {port}'],
                        capture_output=True, text=True, timeout=5
                    )
                    if 'No rules match' in rule_check.stdout:
                        print(f"Port {port}: No specific firewall rule found")
                    else:
                        print(f"Port {port}: Firewall rule exists")
            else:
                print("Windows Firewall: DISABLED")
        else:
            print("Non-Windows OS detected - manual firewall check required")
    except Exception as e:
        print(f"Firewall check failed: {e}")

    print()

    # Instructions
    print("=== TROUBLESHOOTING STEPS ===")
    print()
    print("1. START THE BACKEND SERVER:")
    print("   Option A - Direct Python:")
    print("   cd backend")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8002")
    print()
    print("   Option B - Docker:")
    print("   docker-compose up backend")
    print()

    print("2. IF FIREWALL IS BLOCKING:")
    print("   netsh advfirewall firewall add rule name=\"PC Backend\" dir=in action=allow protocol=TCP localport=8002")
    print("   netsh advfirewall firewall add rule name=\"PC Backend Docker\" dir=in action=allow protocol=TCP localport=8000")
    print()

    print("3. TEST FROM MOBILE DEVICE:")
    print(f"   Direct: http://{local_ip}:8002/docs")
    print(f"   Docker: http://{local_ip}:8000/docs")
    print("   Health: http://{local_ip}:8002/api/v1/health")
    print()

    print("4. COMMON ISSUES:")
    print("   - Server not binding to 0.0.0.0 (check uvicorn command)")
    print("   - Firewall blocking ports")
    print("   - Mobile device on different WiFi network")
    print("   - Using 'localhost' instead of IP address on mobile")
    print("   - Docker container not exposing ports correctly")

if __name__ == "__main__":
    main()