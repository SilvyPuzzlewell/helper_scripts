import requests

from .utils import authorization_header


def create_record(base_url, data, token):
    return requests.post(url=f'{base_url}/api/docs', headers=authorization_header(token), json=data, verify=False)

def create_request(base_url, token, request_type, receiver_type, receiver_id, topic_type, topic_id):
    data = {
        "receiver": {receiver_type: receiver_id},
        "request_type": request_type,
        "topic": {topic_type: topic_id},
    }
    return requests.post(url=f'{base_url}/api/requests', headers=authorization_header(token), json=data,
                         verify=False)