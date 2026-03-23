from google.cloud import secretmanager

_cache = {}
_client = None

def get_secret(name, project='kumori-404602'):
    cache_key = f"{project}:{name}"
    if cache_key in _cache:
        return _cache[cache_key]
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    val = _client.access_secret_version(request={"name": f"projects/{project}/secrets/{name}/versions/latest"}).payload.data.decode('UTF-8')
    _cache[cache_key] = val
    return val
