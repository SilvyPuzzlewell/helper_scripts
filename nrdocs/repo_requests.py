import requests

from .utils import authorization_header

# requests that need more than links for now
def create_record(base_url, data, token, repo="docs"):
    return requests.post(url=f'{base_url}/api/{repo}', headers=authorization_header(token), json=data, verify=False)

def create_record_in_community(base_url, data, token, community_id, repo="docs"):
    return requests.post(f"{base_url}/api/communities/{community_id}/{repo}", headers=authorization_header(token), json=data, verify=False)

def create_request(base_url, token, request_type, topic_type, topic_id):
    data = {
        "request_type": request_type,
        "topic": {topic_type: topic_id},
    }
    return requests.post(url=f'{base_url}/api/requests', headers=authorization_header(token), json=data,
                         verify=False)