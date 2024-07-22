import time

import requests

from .repo_requests import create_record
from .utils import BASE_URL, nrdocs_sample_metadata, authorization_header, \
    ui_serialization_header, upload_file

from invenio_requests.records.api import RequestEventFormat


def test_extended_links(record_id, receiver_token):
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft",
                          headers=authorization_header(receiver_token) | ui_serialization_header(), verify=False).json()
    request = record["requests"][0]
    assert "extended" in request["links"]["self"]
    assert "extended" in request["links"]["comments"]
    assert "extended" in request["links"]["timeline"]
    comment = {
        "payload": {
            "content": "This is a comment.",
            "format": RequestEventFormat.HTML.value,
        }
    }
    self = requests.get(request["links"]["self"], headers=authorization_header(receiver_token), verify=False)
    comments = requests.post(request["links"]["comments"], headers=authorization_header(receiver_token), verify=False, json=comment)

    assert self.status_code == 200
    assert comments.status_code == 201
    #time.sleep(2)
    timeline = requests.get(request["links"]["timeline"], headers=authorization_header(receiver_token), verify=False)
    assert timeline.status_code == 200
    #assert timeline.json()["hits"]["hits"] == 1
    print("self and comment request links tested")

def test_pagination_links(record_id, token):
    records = requests.get(f"{BASE_URL}/api/docs/",
                          headers=authorization_header(token), verify=False).json()
    drafts = requests.get(f"{BASE_URL}/api/user/docs/",
                          headers=authorization_header(token), verify=False).json()
    versions = requests.get(f"{BASE_URL}/api/docs/{record_id}/versions",
                          headers=authorization_header(token), verify=False).json()

    assert "self" in drafts["links"]

def test_owner_draft_access(creator_token, receiver_token, record_id):
    draft_creator = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft",
                                 headers=authorization_header(creator_token),
                                 verify=False).json()
    draft_receiver = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft",
                                 headers=authorization_header(receiver_token),
                                 verify=False).json()
    print()

def requests_listing_performance(creator_token, receiver_token):
    start = time.time()
    listing = requests.get(f"{BASE_URL}/api/requests/?q=&sort=newest&page=1&size=10&is_open=true&mine=true",
                                    headers=authorization_header(creator_token), verify=False).json()
    time_api = time.time() - start
    start = time.time()
    listing_ui = requests.get(f"{BASE_URL}/api/requests/?q=&sort=newest&page=1&size=10&is_open=true&mine=true",
                                    headers=authorization_header(creator_token) | ui_serialization_header(), verify=False).json()
    time_ui = time.time() - start
    print(time_api)
    print(time_ui)


def script(creator_token, receiver_token):
    #sample_record = {"metadata": nrdocs_sample_metadata(), "files": {"enabled": False}}
    sample_record = {"metadata": nrdocs_sample_metadata()}
    #create record
    resp_record = create_record(BASE_URL, sample_record, creator_token)
    upload_file(resp_record.json(), creator_token)
    record_id = resp_record.json()['id']
    if resp_record.status_code != 201:
        print(f"wrong status code {resp_record.status_code}")
        print(resp_record.text)
    assert resp_record.status_code == 201
    print("record created")
    publish_request_by_link = requests.post(resp_record.json()['request_types'][0]['links']['actions']['create'], headers=authorization_header(creator_token), verify=False)
    publish_request_id = publish_request_by_link.json()["id"]
    # publish_request_by_central = create_request(BASE_URL, creator_token, "documents_publish_draft","documents_draft", resp_record.json()["id"])
    assert publish_request_by_link.status_code == 201
    request_detail = requests.get(publish_request_by_link.json()['links']['self'], headers=authorization_header(creator_token), verify=False).json()
    request_detail_ui_serialization = requests.get(publish_request_by_link.json()['links']['self'], headers=authorization_header(creator_token) | ui_serialization_header(), verify=False).json()
    print("request created")
    submit_request = requests.post(request_detail_ui_serialization['links']['actions']['submit'], headers=authorization_header(creator_token), verify=False)
    print("request submitted")
    # test that publish request is on the record
    test_owner_draft_access(creator_token, receiver_token, record_id)

    draft_receiver = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(receiver_token) | ui_serialization_header(), verify=False).json()
    draft_creator = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(creator_token) | ui_serialization_header(), verify=False).json()

    test_extended_links(record_id, receiver_token)
    test_pagination_links(record_id, creator_token)
    #accept_request = requests.get(f"{BASE_URL}/api/requests/{request_detail['id']}", headers=authorization_header(receiver_token), verify=False).json()

    receiver_request = requests.get(f"{BASE_URL}/api/requests/{publish_request_id}", headers=authorization_header(receiver_token), verify=False).json()


    accept = requests.post(receiver_request['links']['actions']['accept'], headers=authorization_header(receiver_token), verify=False)
    assert accept.status_code == 200
    print("request accepted")

    requests.get(f"{BASE_URL}/api/global-search", headers=authorization_header(receiver_token), verify=False)
    published_record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(receiver_token), verify=False).json()
    published_record_ui = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(receiver_token)
                                                                                                  | ui_serialization_header(), verify=False).json()


    # TODO? api call to get request types for topic type?
    delete_request = requests.post(published_record_ui['request_types'][0]['links']['actions']['create'], headers=authorization_header(creator_token), verify=False)
    assert delete_request.status_code == 201
    print("delete request created")
    submit_request = requests.post(delete_request.json()['links']['actions']['submit'],
                                   headers=authorization_header(creator_token), verify=False)
    assert submit_request.status_code == 200
    print("delete request submitted")
    """
    record = requests.get(f"{BASE_URL}/api/docs/{resp_record.json()['id']}", headers=authorization_header(receiver_token)
                                                                                                  | ui_serialization_header(), verify=False).json()
    accept = requests.post(record['requests'][0]['links']['actions']['accept'],
                           headers=authorization_header(receiver_token), verify=False)
    assert accept.status_code == 200
    print("delete request accepted")
    deleted_record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(receiver_token),
                 verify=False)
    assert deleted_record.status_code == 410
    print("record deleted")
    """

