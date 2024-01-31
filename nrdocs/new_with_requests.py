import requests

from .repo_requests import create_record, create_request
from .utils import nrdocs_sample_record, BASE_URL, nrdocs_sample_metadata, authorization_header, ui_serialization_header


def script(token):
    sample_record = {"metadata": nrdocs_sample_metadata(), "files": {"enabled": False}}
    #create record
    resp_record = create_record(BASE_URL, sample_record, token)
    if resp_record.status_code != 201:
        print(f"wrong status code {resp_record.status_code}")
        print(resp_record.text)
    assert resp_record.status_code == 201
    print("record created")

    publish_request = create_request(BASE_URL, token, "publish_draft", "user", "2", "documents_draft", resp_record.json()["id"])
    assert publish_request.status_code == 201
    request_detail = requests.get(publish_request.json()['links']['self'], headers=authorization_header(token), verify=False).json()
    request_detail_ui_serialization = requests.get(publish_request.json()['links']['self'], headers=authorization_header(token) | ui_serialization_header(), verify=False).json()
    print("request created")

    """
    #publish record
    resp = requests.post(url=f'{BASE_URL}/api/requests/{request_id}/actions/submit', headers=header, verify=False)
    if resp.status_code != 200:
        print(f"wrong status code {resp.status_code}")
        print(resp.text)
    assert resp.status_code == 200
    print("record published")
    """