import copy
import logging
import sys

import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
BASE_URL = "https://127.0.0.1:5000"

FILE_METADATA = [
    {
        "metadata": {
            "title": "blabla"
        },
        "key": "crap.jpg"
    }
]

def _check_status_code(resp, correct_code, message):
    if resp.status_code != correct_code:
        print(message)
        print(f"wrong status code {resp.status_code}")
        print(resp.text)
    assert resp.status_code == correct_code


def json_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

def headers(token):
    return {
        'Authorization': f'Bearer {token}',
    }
"""
COMMUNITY_SLUG = "tst3"
SIMPLE_COMMUNITY = {
        "slug": "tst3",
        "access": {
            "visibility": "public"
        },
        "metadata": {
            "title": "Test3",
            "type": {
                "id": "topic"
            }
        }
    }

SIMPLE_COMMUNITY_2 = {
        "slug": "tst4",
        "access": {
            "visibility": "public"
        },
        "metadata": {
            "title": "Test4",
            "type": {
                "id": "event"
            }
        }
    }

COMMUNITY_CF = {
    "custom_fields": {
        "permissions": {
            "owner": {
                "can_search": True,
                "can_publish": True,
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": True,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": True,
                "can_remove_records_from_community": True,
            },
            "manager": {
                "can_publish": True,
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": True,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": True,
                "can_remove_records_from_community": True,
            },
            "curator": {
                "can_create": True,
                "can_read": True,
                "can_update": True,
                "can_delete": False,
                "can_community_allows_adding_records": True,
                "can_remove_community_from_record": False,
                "can_remove_records_from_community": False,
            },
            "reader": {
                "can_create": False,
                "can_read": True,
                "can_update": False,
                "can_delete": False,
                "can_community_allows_adding_records": False,
                "can_remove_community_from_record": False,
                "can_remove_records_from_community": False,
            }
        },
        "aai_mapping": [
            {
                "role": "curator",
                "aai_group": "urn:geant:cesnet.cz:group:VO_nrp_development:test_community:curator#perun.cesnet.cz"
            }
        ]
    },
    "slug": "tst3",
    "metadata": {
        "title": "Test2",
        "type": {
            "id": "topic"
        }
    },
    "access": {
        "member_policy": "open",
        "record_policy": "open",
        "visibility": "public"
    }
}
"""
def nrdocs_sample_record():
    return json.load(open("sample_record.json", 'r'))

def upload_file(record_resp, headers):
    link = record_resp.json()["links"]["files"]
    resp_create = requests.post(link, headers=headers, json=FILE_METADATA, verify=False)
    file_upload_headers = copy.deepcopy(headers)
    file_upload_headers["Content-Type"] = "application/octet-stream"
    with open('file.jpg', 'rb') as f:
        data = f.read()
    resp_content = requests.put(resp_create.json()["entries"][0]["links"]["content"], headers=file_upload_headers, data=data, verify=False)
    resp_commit = requests.post(resp_create.json()["entries"][0]["links"]["commit"], headers=headers, verify=False)
    return resp_create, resp_content, resp_commit


def init_with_files(token):
    header = headers(token)
    jheader = json_headers(token)
    #create record
    resp_record = requests.post(url=f'{BASE_URL}/api/nr-documents', headers=jheader, json=nrdocs_sample_record(), verify=False)
    _check_status_code(resp_record, 201, "draft create")
    print("record created")

    record_id = resp_record.json()["id"]
    request_id = resp_record.json()['parent']['publish_draft']['id']

    resp_create, resp_content, resp_commit = upload_file(resp_record, jheader)

    #publish record
    resp = requests.post(url=f'{BASE_URL}/api/requests/{request_id}/actions/submit', headers=header, verify=False)
    _check_status_code(resp, 200, "publish")
    print("record published")

    published_record_resp = requests.get(resp_record.json()["links"]["record"], headers=jheader, verify=False)
    _check_status_code(published_record_resp, 200, "published record get")
    published_record_files = requests.get(published_record_resp.json()["links"]["files"], headers=jheader, verify=False)
    _check_status_code(published_record_files, 200, "published record files get")
    file_self = requests.get(published_record_files.json()["entries"][0]["links"]["self"], headers=header, verify=False)
    _check_status_code(file_self, 200, "published record file 0 get")
    file_content = requests.get(published_record_files.json()["entries"][0]["links"]["content"], headers=header, verify=False)
    _check_status_code(file_content, 200, "published record file 0 content")
    requests.get(file_content.text)

def init_without_files(token):
    header = headers(token)
    jheader = json_headers(token)
    sample_record = nrdocs_sample_record() | {"files": {"enabled": False}}
    #create record
    resp_record = requests.post(url=f'{BASE_URL}/api/nr-documents', headers=jheader, json=sample_record, verify=False)
    if resp_record.status_code != 201:
        print(f"wrong status code {resp_record.status_code}")
        print(resp_record.text)
    assert resp_record.status_code == 201
    print("record created")

    record_id = resp_record.json()["id"]
    request_id = resp_record.json()['parent']['publish_draft']['id']

    #publish record
    resp = requests.post(url=f'{BASE_URL}/api/requests/{request_id}/actions/submit', headers=header, verify=False)
    if resp.status_code != 200:
        print(f"wrong status code {resp.status_code}")
        print(resp.text)
    assert resp.status_code == 200
    print("record published")


"""
def init_with_communities(token):
    header = headers(token)
    jheader = json_headers(token)

    #create community
    resp = requests.post(url=f'{BASE_URL}/api/communities', headers=jheader, json=SIMPLE_COMMUNITY, verify=False)
    assert resp.status_code == 201
    print("community created")

    #upload community cf
    resp = requests.put(url=f'{BASE_URL}/api/communities/{COMMUNITY_SLUG}', headers=jheader, json=COMMUNITY_CF, verify=False)
    assert resp.status_code == 200
    print("custom fields uploaded")


    #create record
    comm_id = requests.get(url=f'{BASE_URL}/api/communities/{COMMUNITY_SLUG}', headers=header, verify=False).json()["id"]
    resp = requests.post(url=f'{BASE_URL}/api/nr-documents', headers=jheader, json=nrdocs_sample_record() | {"community_id": comm_id}, verify=False)
    record_id = resp.json()["id"]
    request_id = resp.json()['parent']['publish_draft']['id']
    assert resp.status_code == 201
    print("record created")

    #publish record
    resp = requests.post(url=f'{BASE_URL}/api/requests/{request_id}/actions/submit', headers=header, verify=False)
    assert resp.status_code == 200
    print("record published")

    #test community records
    resp = requests.get(url=f"{BASE_URL}/api/communities/{comm_id}/records", headers=header, verify=False)
    assert resp.status_code == 200
    assert len(resp.json()['hits']['hits']) >= 0
    print("community records test passed")

    #create second community
    resp = requests.post(url=f'{BASE_URL}/api/communities', headers=jheader, json=SIMPLE_COMMUNITY_2, verify=False)
    assert resp.status_code == 201
    print("community created")

    first_community_input = {
        "communities": [
            {"id": "tst3"}
        ]
    }

    second_community_input = {
        "communities": [
            {"id": "tst4"}
        ]
    }

    #add second community on first record
    #resp = requests.post(url=f'{BASE_URL}/api/nr-documents/{record_id}', headers=jheader, json=second_community_input, verify=False)
    #assert resp.status_code == 200
    #print("second community added on record")

    #remove first community from input
    #resp = requests.delete(url=f'{BASE_URL}/api/nr-documents/{record_id}', headers=jheader, json=first_community_input, verify=False)
    #assert resp.status_code == 200
    #print("second community added on record")

    #remove record from first community
"""
    





if __name__ == "__main__":
    token = sys.argv[1]
    func = sys.argv[2]

    function_to_call = globals().get(func, None)

    # Call the function if it exists
    if callable(function_to_call):
        function_to_call(token)













