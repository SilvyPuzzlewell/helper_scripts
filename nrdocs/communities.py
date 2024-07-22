import time
import requests

from nrdocs.repo_requests import create_record, create_record_in_community
from nrdocs.utils import authorization_header, BASE_URL, nrdocs_sample_metadata, _find_request_from_search_by_type, \
    create_request_on_record, upload_file

COMMUNITY_DICT = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "praguecommune",
        "metadata": {
            "title": "prague commune",
        },
    }

COMMUNITY_DICT2 = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "pilsencommune",
        "metadata": {
            "title": "pilsen commune",
        },
    }

COMMUNITY_DICT3 = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "brnocommune",
        "metadata": {
            "title": "brno commune",
        },
    }

COMMUNITY_PERMISSIONS_CF = {
        "custom_fields": {
            "permissions": {
                "owner": {
                    "can_create_in_community": True,
                    "can_submit_to_community": True,
                    "can_submit_secondary_community": True,
                    "can_remove_secondary_community": True,
                    "can_publish_request": True,
                    "can_delete_request": True,
                    "can_read": True,
                    "can_read_draft": True,
                    "can_update": True,
                    "can_create": True,
                    "can_create_invitation": True,
                    "can_draft_create_files": True,
                    "can_draft_set_content_files": True,
                    "can_draft_get_content_files": True,
                    "can_draft_commit_files": True,
                    "can_draft_read_files": True,
                    "can_draft_update_files": True,
                },
                "reader": {
                    "can_create_in_community": True,
                    "can_submit_to_community": False,
                    "can_submit_secondary_community": False,
                    "can_remove_secondary_community": False,
                    "can_publish_request": False,
                    "can_delete_request": False,
                    "can_read": True,
                    "can_read_draft": True,
                    "can_update": False,
                    "can_delete": False,
                },
            }
        }
    }

def invite(user_id, community_id, role, owner_token, reader_token):
    """Add/invite a user to a community with a specific role."""
    invitation_data = {
        "members": [{"type": "user", "id": user_id}],
        "role": "reader",
        "message": "Welcome to the club!",

    }

    r = requests.get(
        f"{BASE_URL}/api/communities/{community_id}/members",
        headers=authorization_header(owner_token),
        verify=False
    )
    if len(r.json()["hits"]["hits"]) > 1:
        return

    r = requests.post(
        f"{BASE_URL}/api/communities/{community_id}/invitations",
        headers=authorization_header(owner_token),
        json=invitation_data,
        verify=False,
    )
    assert r.status_code == 204



    reader_requests = requests.get(f"{BASE_URL}/api/user/requests", headers=authorization_header(reader_token), verify=False)
    request = _find_request_from_search_by_type(reader_requests, "community-invitation", topic={'community': community_id})
    accept = requests.post(request["links"]["actions"]["accept"], headers=authorization_header(reader_token), verify=False)
    r = requests.get(
        f"{BASE_URL}/api/communities/{community_id}/members",
        headers=authorization_header(owner_token),
        verify=False
    )
    return r


def publish_request_data(draft_id):
    return {'request_type': 'documents_publish_draft', 'topic': {'documents_draft': draft_id}}

def get_community_from_results(result_response, slug):
    hits = result_response.json()["hits"]["hits"]
    for hit in hits:
        if hit["slug"] == slug:
            return hit
    return None
def create_community(creator_token, permissions_cf=None, community_dict=None):
    if not permissions_cf:
        permissions_cf = COMMUNITY_PERMISSIONS_CF
    if not community_dict:
        community_dict = COMMUNITY_DICT
    user_communities = requests.get(f"{BASE_URL}/api/user/communities", headers=authorization_header(creator_token), verify=False)
    existing_comm = get_community_from_results(user_communities, community_dict["slug"])
    if not existing_comm:
        comm = requests.post(f"{BASE_URL}/api/communities", headers=authorization_header(creator_token), json=community_dict, verify=False).json()
    else:
        comm = existing_comm
    data = comm | permissions_cf
    update = requests.put(f"{BASE_URL}/api/communities/{comm['id']}", headers=authorization_header(creator_token), json=data, verify=False)
    return update

def invite_reader():
    """"""

def do_request(owner_token, reader_token, record_id, type, payload=None, is_draft=False):
    url = f"{BASE_URL}/api/docs/{record_id}/draft" if is_draft else f"{BASE_URL}/api/docs/{record_id}"
    record_resp = requests.get(url, headers=authorization_header(reader_token), verify=False)
    #todo CommunityAlreadyIncludedException should throw 500 (400 instead)??
    request = create_request_on_record(record_resp, type, reader_token, data=payload)
    assert request.status_code == 201
    submit = requests.post(request.json()["links"]["actions"]["submit"],
                           headers=authorization_header(reader_token), verify=False)
    assert submit.status_code == 200
    request_receiver = requests.get(f"{BASE_URL}/api/requests/{submit.json()['id']}", headers=authorization_header(owner_token), verify=False)
    accept = requests.post(request_receiver.json()["links"]["actions"]["accept"],
                           headers=authorization_header(owner_token), verify=False)
    assert accept.status_code == 200
def script(owner_token, reader_token):
    community =  create_community(owner_token)
    invite('2', community.json()["id"], "reader", owner_token, reader_token)
    community2 = create_community(owner_token, community_dict=COMMUNITY_DICT2)
    invite('2', community2.json()["id"], "reader", owner_token, reader_token)
    community3 = create_community(owner_token, community_dict=COMMUNITY_DICT3)
    invite('2', community3.json()["id"], "reader", owner_token, reader_token)

    sample_record = {"metadata": nrdocs_sample_metadata()}

    resp_record = create_record(BASE_URL, sample_record, owner_token)
    assert resp_record.status_code == 403
    # todo draft request entrypoints are still not propagated correctly
    # todo how do entrypoints work in nr-docs pyproject.toml???
    resp_record = create_record_in_community(BASE_URL, sample_record, reader_token, community.json()["id"], repo="docs")
    record_id = resp_record.json()["id"]
    upload_file(resp_record.json(), owner_token)
    time.sleep(2)
    do_request(owner_token, reader_token, record_id, 'documents_publish_draft', is_draft=True)

    #test submit secondary
    time.sleep(2)
    payload = {'payload': {'community': community2.json()["id"]}}
    do_request(owner_token, reader_token, record_id, "documents_secondary_community_submission", payload)

    #test migrate
    payload = {'payload': {'community': community3.json()["id"]}}
    do_request(owner_token, reader_token, record_id, "documents_community_migration", payload)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(reader_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community2.json()["id"], community3.json()["id"]}
    assert record_communities["default"] == community3.json()["id"]

    # todo global search service bug - thesis service added twice from eps!!
    record_communities_search = requests.get(f"{BASE_URL}/api/docs/{record_id}/communities", headers=authorization_header(reader_token), verify=False)
    community_records = requests.get(f"{BASE_URL}/api/communities/{community.json()['id']}/records", headers=authorization_header(reader_token), verify=False)

    #test remove secondary
    payload = {'payload': {'community': community2.json()["id"]}}
    do_request(owner_token, reader_token, record_id, "documents_remove_secondary_community", payload)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(reader_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community3.json()["id"]}

    #test delete record
    delete_directly = requests.delete(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(owner_token), verify=False)
    assert delete_directly.status_code == 403

    do_request(owner_token, reader_token, record_id, "documents_delete_record")
    time.sleep(2)
    record_resp = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(reader_token), verify=False)
    assert record_resp.status_code == 410



