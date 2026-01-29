import json
import urllib.request
import urllib.parse
import argparse
import sys
import time

def queue_prompt(prompt_workflow, server_address):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    url = "http://{}/prompt".format(server_address)
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Error connecting to ComfyUI at {server_address}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Trigger ComfyUI Workflow")
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON file")
    parser.add_argument("--ip", required=True, help="RunPod IP address")
    parser.add_argument("--port", default="8188", help="RunPod HTTP Port")
    
    args = parser.parse_args()
    
    server_address = f"{args.ip}:{args.port}"
    
    print(f"Loading workflow from {args.workflow}...")
    try:
        with open(args.workflow, 'r') as f:
            workflow = json.load(f)
    except FileNotFoundError:
        print("Workflow file not found.")
        sys.exit(1)
        
    # TODO: Add logic here to inject dynamic parameters into the workflow if needed
    # (e.g., search for a node with "inputs": {"text": ...} and replace it)

    print(f"Queueing prompt on {server_address}...")
    response = queue_prompt(workflow, server_address)
    print("Response:", response)

if __name__ == "__main__":
    main()
