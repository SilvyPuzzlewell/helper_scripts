from nrdocs.repo_requests import create_record, create_request
from nrdocs.utils import BASE_URL, mbdb_sample_metadata, authorization_header
import requests

def script(creator_token, receiver_token):
    sample_data = mbdb_sample_metadata()
    def create_mbdb_record(type):
        sample_record = sample_data[type][0]["metadata"]
        # create record
        resp_record = create_record(BASE_URL, sample_record, creator_token, repo=f"records/{type}")
        record_id = resp_record.json()['id']
        if resp_record.status_code != 201:
            print(f"wrong status code {resp_record.status_code} for record of type {type}")
            print(resp_record.text)
        assert resp_record.status_code == 201
        print(f"record of type {type} created")
        return resp_record

    def publish_mbdb_record(record_id, type):
        # todo - perhaps auto decide topic type instead of sending it in request; ie. whether this is possibe depends whether it has unique id; probably doesn't...
        request = create_request(BASE_URL, creator_token, "publish_draft", "user", "2", f"{type}_draft",
                       record_id)
        request_detail = requests.get(request.json()['links']['self'],
                                      headers=authorization_header(creator_token), verify=False).json()
        submit_request = requests.post(request_detail['links']['actions']['submit'],
                                       headers=authorization_header(creator_token), verify=False)
        record = requests.get(f"{BASE_URL}/api/records/{type}/{record_id}/draft",
                              headers=authorization_header(receiver_token),
                              verify=False).json()
        return requests.post(record['requests'][0]['links']['actions']['accept'],
                               headers=authorization_header(receiver_token), verify=False)
    mst = create_mbdb_record("mst")
    spr = create_mbdb_record("spr")
    bli = create_mbdb_record("bli")

    #acc = publish_mbdb_record(mst.json()["id"], "mst")

    global_search = requests.get(f"{BASE_URL}/api/user/search", headers=authorization_header(receiver_token), verify=False)
    jsn = global_search.json()
    print()


    """
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
    time.sleep(1)

    requests.get(f"{BASE_URL}/api/global-search", headers=authorization_header(receiver_token), verify=False)
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
    """