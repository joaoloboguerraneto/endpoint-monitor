#!/usr/bin/env python3
"""
Endpoint Monitor - A CLI tool to test if websites or services are available

This tool allows you to:
- Add endpoints to a configuration file
- Scan all configured endpoints
- Continuously monitor endpoints at specified intervals
- View the history of scan results
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
import csv
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Union, Any

# Configuration and data store paths
CONFIG_DIR = os.path.expanduser("~/.endpoint-monitor")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATA_STORE_FILE = os.path.join(CONFIG_DIR, "data-store.csv")

# Default settings
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_POLLING_INTERVAL = 60  # seconds

# Ensure configuration directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)


class EndpointMonitor:
    """Main class for handling endpoint monitoring functionality"""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from file or create default if it doesn't exist"""
        if not os.path.exists(CONFIG_FILE):
            default_config = {"endpoints": {}}
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Config file {CONFIG_FILE} is corrupted")
            sys.exit(1)

    def _save_config(self):
        """Save current configuration to file"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def add_endpoint(self, name: str, url: str, timeout: int = DEFAULT_TIMEOUT):
        """Add a new endpoint to the configuration"""
        if name in self.config["endpoints"]:
            print(f"Error: Endpoint '{name}' already exists")
            return False

        self.config["endpoints"][name] = {
            "url": url,
            "timeout": timeout
        }
        self._save_config()
        print(f"Added endpoint: {name} ({url}) with timeout {timeout}s")
        return True

    def _check_endpoint(self, name: str, endpoint_data: Dict) -> Dict:
        """Check if an endpoint is available"""
        url = endpoint_data["url"]
        timeout = endpoint_data.get("timeout", DEFAULT_TIMEOUT)
        
        timestamp = datetime.now().isoformat()
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            response_time = time.time() - start_time
            
            status_code = response.status_code
            is_available = 200 <= status_code < 400
            
            result = {
                "name": name,
                "url": url,
                "timestamp": timestamp,
                "status_code": status_code,
                "response_time": round(response_time * 1000, 2),  # convert to ms
                "is_available": is_available
            }
            
        except requests.exceptions.RequestException as e:
            result = {
                "name": name,
                "url": url,
                "timestamp": timestamp,
                "status_code": None,
                "response_time": None,
                "is_available": False,
                "error": str(e)
            }
            
        return result

    def _save_result(self, result: Dict):
        """Save a scan result to the data store"""
        file_exists = os.path.exists(DATA_STORE_FILE)
        
        with open(DATA_STORE_FILE, "a", newline="") as f:
            fieldnames = [
                "name", "url", "timestamp", "status_code", 
                "response_time", "is_available", "error"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(result)

    def fetch(self, endpoint_names: Optional[List[str]] = None, output: bool = False) -> List[Dict]:
        """Scan specified endpoints or all if none specified"""
        endpoints = self.config["endpoints"]
        
        if not endpoints:
            print("No endpoints configured. Use 'add-endpoint' command to add some.")
            return []
            
        # Filter endpoints if names provided
        if endpoint_names:
            to_check = {name: endpoints[name] for name in endpoint_names if name in endpoints}
            if not to_check:
                print("No matching endpoints found")
                return []
        else:
            to_check = endpoints
            
        results = []
        
        # Use ThreadPoolExecutor to check endpoints concurrently
        with ThreadPoolExecutor() as executor:
            future_to_endpoint = {
                executor.submit(self._check_endpoint, name, data): name 
                for name, data in to_check.items()
            }
            
            for future in future_to_endpoint:
                result = future.result()
                results.append(result)
                self._save_result(result)
                
        # Output results if requested
        if output:
            self._print_results(results)
            
        return results

    def _print_results(self, results: List[Dict]):
        """Print scan results in a table format"""
        if not results:
            print("No results to display")
            return
            
        # Calculate column widths
        col_widths = {
            "name": max(len("ENDPOINT"), max(len(r["name"]) for r in results)),
            "url": max(len("URL"), max(len(r["url"]) for r in results)),
            "status": len("STATUS"),
            "response_time": len("RESPONSE TIME (ms)"),
        }
        
        # Print header
        print(
            f"{'ENDPOINT':<{col_widths['name']}} "
            f"{'URL':<{col_widths['url']}} "
            f"{'STATUS':<{col_widths['status']}} "
            f"{'RESPONSE TIME (ms)':<{col_widths['response_time']}} "
            f"TIMESTAMP"
        )
        print("-" * (col_widths['name'] + col_widths['url'] + col_widths['status'] + col_widths['response_time'] + 50))
        
        # Print each result
        for r in results:
            status = "UP" if r["is_available"] else "DOWN"
            status_color = "\033[92m" if r["is_available"] else "\033[91m"  # Green for UP, Red for DOWN
            reset_color = "\033[0m"
            
            response_time = str(r["response_time"]) if r["response_time"] is not None else "N/A"
            
            print(
                f"{r['name']:<{col_widths['name']}} "
                f"{r['url']:<{col_widths['url']}} "
                f"{status_color}{status:<{col_widths['status']}}{reset_color} "
                f"{response_time:<{col_widths['response_time']}} "
                f"{r['timestamp']}"
            )

    def live(self, interval: int = DEFAULT_POLLING_INTERVAL, endpoint_names: Optional[List[str]] = None, output: bool = False):
        """Continuously monitor endpoints at specified intervals"""
        try:
            print(f"Starting live monitoring with interval {interval}s. Press Ctrl+C to stop.")
            
            while True:
                results = self.fetch(endpoint_names, output=output)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nLive monitoring stopped")

    def history(self, endpoint_names: Optional[List[str]] = None):
        """Show scan history from the data store"""
        if not os.path.exists(DATA_STORE_FILE):
            print("No history available yet")
            return
            
        results = []
        
        with open(DATA_STORE_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Convert string values to appropriate types
                row["is_available"] = row["is_available"].lower() == "true"
                
                if row["status_code"] and row["status_code"] != "None":
                    row["status_code"] = int(row["status_code"])
                else:
                    row["status_code"] = None
                    
                if row["response_time"] and row["response_time"] != "None":
                    row["response_time"] = float(row["response_time"])
                else:
                    row["response_time"] = None
                
                # Filter by endpoint names if provided
                if endpoint_names and row["name"] not in endpoint_names:
                    continue
                    
                results.append(row)
                
        self._print_results(results)


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Monitor website or service availability")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # add-endpoint command
    add_parser = subparsers.add_parser("add-endpoint", help="Add an endpoint configuration")
    add_parser.add_argument("name", help="Name of the endpoint")
    add_parser.add_argument("url", help="URL of the endpoint")
    add_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    
    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Scan all configured endpoints")
    fetch_parser.add_argument("--output", action="store_true", help="Output the result of the scan")
    fetch_parser.add_argument("--endpoints", nargs="+", help="Specific endpoints to scan")
    
    # live command
    live_parser = subparsers.add_parser("live", help="Continuously scan endpoints at specified intervals")
    live_parser.add_argument("--interval", type=int, default=DEFAULT_POLLING_INTERVAL, help="Polling interval in seconds")
    live_parser.add_argument("--output", action="store_true", help="Output scan results")
    live_parser.add_argument("--endpoints", nargs="+", help="Specific endpoints to scan")
    
    # history command
    history_parser = subparsers.add_parser("history", help="Show scan history")
    history_parser.add_argument("--endpoints", nargs="+", help="Show history for specific endpoints only")
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = EndpointMonitor()
    
    # Execute command
    if args.command == "add-endpoint":
        monitor.add_endpoint(args.name, args.url, args.timeout)
        
    elif args.command == "fetch":
        monitor.fetch(args.endpoints, args.output)
        
    elif args.command == "live":
        monitor.live(args.interval, args.endpoints, args.output)
        
    elif args.command == "history":
        monitor.history(args.endpoints)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()