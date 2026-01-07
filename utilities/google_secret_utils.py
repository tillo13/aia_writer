from google.cloud import secretmanager

def get_secret(name, project='kumori-404602'):
    client = secretmanager.SecretManagerServiceClient()
    return client.access_secret_version(request={"name": f"projects/{project}/secrets/{name}/versions/latest"}).payload.data.decode('UTF-8')
