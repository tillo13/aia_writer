#!/usr/bin/env python3
import subprocess
import json
import time
import os
import sys

EXPECTED_PROJECT_ID = "aia-writer-2025"
SERVICE_NAME = "default"
VERSION_MAX = 5

def print_separator():
    print("\n" + "="*70 + "\n")

def check_required_files():
    print("Checking required files...")
    required_files = {
        'app.yaml': 'App Engine configuration file',
        'app.py': 'Main application file',
        'requirements.txt': 'Python dependencies file'
    }
    
    all_present = True
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"✓ {filename} - {description}")
        else:
            print(f"✗ {filename} - {description} - MISSING!")
            all_present = False
    
    if not all_present:
        print("\nERROR: Missing required files for deployment!")
        sys.exit(1)
    
    print("\nChecking requirements.txt content...")
    with open('requirements.txt', 'r') as f:
        requirements = f.read().strip()
        if not requirements:
            print("ERROR: requirements.txt is empty!")
            sys.exit(1)
        
        if 'gunicorn' not in requirements.lower():
            print("\nWARNING: gunicorn not found in requirements.txt!")
            sys.exit(1)
    
    print("\nAll required files present and valid.")

def check_gcloud_project():
    print_separator()
    print("Verifying Google Cloud project configuration...")
    
    try:
        current_project = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        ).stdout.decode().strip()
        
        print(f"Current Google Cloud project: {current_project}")
        
        if current_project != EXPECTED_PROJECT_ID:
            print(f"Switching to {EXPECTED_PROJECT_ID}...")
            subprocess.run(
                ["gcloud", "config", "set", "project", EXPECTED_PROJECT_ID],
                check=True
            )
            print(f"Successfully switched to project {EXPECTED_PROJECT_ID}")
        else:
            print(f"Correctly configured for project {EXPECTED_PROJECT_ID}")
    
    except subprocess.CalledProcessError as e:
        print(f"Error checking Google Cloud project: {e}")
        sys.exit(1)

def get_versions():
    print("Checking existing versions...")
    try:
        result = subprocess.run(
            ["gcloud", "app", "versions", "list", 
             "--service", SERVICE_NAME, 
             "--format", "json", 
             "--project", EXPECTED_PROJECT_ID],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        versions = json.loads(result.stdout)
        versions.sort(key=lambda x: x["version"]["createTime"], reverse=True)
        return versions
    except subprocess.CalledProcessError as e:
        if "Service [default] not found" in e.stderr.decode():
            print(f"Service {SERVICE_NAME} not found. Proceeding with deployment...")
            return []
        else:
            print(f"Error: {e.stderr.decode()}")
            raise e

def delete_old_versions(versions_to_delete):
    if not versions_to_delete:
        return
    
    print(f"Cleaning up old versions. Deleting {len(versions_to_delete)} older versions...")
    
    for v in versions_to_delete:
        version_id = v["id"]
        print(f"  - Deleting version {version_id}")
        subprocess.run(
            ["gcloud", "app", "versions", "delete", version_id, 
             "--service", SERVICE_NAME, 
             "--quiet", 
             "--project", EXPECTED_PROJECT_ID],
            check=True)
    
    print("Cleanup complete.")

def deploy_app():
    start_time = time.time()
    
    print_separator()
    check_required_files()
    check_gcloud_project()
    
    current_dir = os.getcwd()
    yaml_path = os.path.join(current_dir, "app.yaml")
    
    print_separator()
    print("Deploying AIA Writer to Google App Engine...")
    print(f"Project: {EXPECTED_PROJECT_ID}")
    print(f"Service: {SERVICE_NAME}")
    print_separator()
    
    versions = get_versions()
    current_version_count = len(versions)
    print(f"You currently have {current_version_count} versions of the service.")
    
    if current_version_count > 0:
        print(f"The latest version is {versions[0]['id']}.")
    
    print_separator()
    print("Deploying new version...")
    subprocess.run(
        ["gcloud", "app", "deploy", yaml_path, 
         "--quiet", 
         "--project", EXPECTED_PROJECT_ID],
        check=True)
    print("Deployment successful!")
    
    if current_version_count >= VERSION_MAX:
        print_separator()
        updated_versions = get_versions()
        versions_to_delete = updated_versions[VERSION_MAX:]
        delete_old_versions(versions_to_delete)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print_separator()
    print(f"Deployment completed in {execution_time:.2f} seconds.")
    print(f"Your app is now live at:")
    print(f"  - https://{EXPECTED_PROJECT_ID}.wm.r.appspot.com")
    print_separator()

if __name__ == "__main__":
    deploy_app()