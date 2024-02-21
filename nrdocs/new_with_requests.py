import shutil

import requests

from .repo_requests import create_record, create_request
from .utils import nrdocs_sample_record, BASE_URL, nrdocs_sample_metadata, authorization_header, \
    ui_serialization_header, file_content_header


def upload_file(record, token):
    data_json = [
    {
        "metadata": {
            "title": "blabla"
        },
        "key": "file.jpg"
    }
]
    file_path = "file.jpg"
    file = open(file_path, 'rb')
    files = {'file': file}
    initiate_upload = requests.post(record["links"]["files"], headers=authorization_header(token), json=data_json, verify=False)
    upload_link = initiate_upload.json()['entries'][0]['links']['content']
    commit_link = initiate_upload.json()['entries'][0]['links']['commit']
    upload = requests.put(upload_link, headers=authorization_header(token)|file_content_header(), files=files, verify=False)
    commit = requests.post(commit_link, headers=authorization_header(token), verify=False)
    response = requests.get(upload_link, stream=True, headers=authorization_header(token), verify=False)
    response2 = requests.get(response.raw.data.decode('utf-8'), stream=True, headers=authorization_header(token), verify=False)
    with open('check_img.png', 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)

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

    publish_request = create_request(BASE_URL, creator_token, "documents_draft_publish_draft", "user", "2", "documents_draft", resp_record.json()["id"])
    assert publish_request.status_code == 201
    request_detail = requests.get(publish_request.json()['links']['self'], headers=authorization_header(creator_token), verify=False).json()
    request_detail_ui_serialization = requests.get(publish_request.json()['links']['self'], headers=authorization_header(creator_token) | ui_serialization_header(), verify=False).json()
    print("request created")
    submit_request = requests.post(request_detail['links']['actions']['submit'], headers=authorization_header(creator_token), verify=False)
    print("request submitted")
    # test that publish request is on the record
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(receiver_token) | ui_serialization_header(), verify=False).json()
    #accept_request = requests.get(f"{BASE_URL}/api/requests/{request_detail['id']}", headers=authorization_header(receiver_token), verify=False).json()
    accept = requests.post(record['requests'][0]['links']['actions']['accept'], headers=authorization_header(receiver_token), verify=False)
    assert accept.status_code == 200
    print("request accepted")

    published_record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(receiver_token), verify=False).json()
    published_record_ui = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(receiver_token)
                                                                                                  | ui_serialization_header(), verify=False).json()

    # TODO? api call to get request types for topic type?
    delete_request = create_request(BASE_URL, creator_token, "documents_delete_record", "user", "2", "documents", resp_record.json()["id"])
    assert delete_request.status_code == 201
    print("delete request created")
    submit_request = requests.post(delete_request.json()['links']['actions']['submit'],
                                   headers=authorization_header(creator_token), verify=False)
    assert submit_request.status_code == 200
    print("delete request submitted")
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
