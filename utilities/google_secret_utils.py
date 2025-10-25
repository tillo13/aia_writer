"""Google Secret Manager utilities for kumori apps"""
import subprocess
from google.cloud import secretmanager

def get_secret(secret_id: str, project_id: str = "kumori-404602"):
    """Get secret from GCP Secret Manager with auto project switching"""
    original = subprocess.run(['gcloud','config','get-value','project'], capture_output=True, text=True).stdout.strip()
    if original != project_id:
        subprocess.run(['gcloud','config','set','project',project_id], capture_output=True)
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        secret = client.access_secret_version(request={"name": name}).payload.data.decode('UTF-8')
        if original != project_id:
            subprocess.run(['gcloud','config','set','project',original], capture_output=True)
        return secret
    except Exception as e:
        if original != project_id:
            subprocess.run(['gcloud','config','set','project',original], capture_output=True)
        return None