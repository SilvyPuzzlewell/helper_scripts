import time
import requests
from nrdocs.repo_requests import create_record, create_record_in_community
from nrdocs.utils import authorization_header, BASE_URL, nrdocs_sample_metadata, _find_request_from_search_by_type, \
    create_request_on_record, upload_file, _find_request_by_type_id, nrdocs_sample_matadata_missing_required_fields, \
    nrdocs_sample_metadata_custom, ui_serialization_header
import arrow
from unittest import mock
from datetime import datetime
from dateutil import tz

COMMUNITY_DICT = {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": "generic",
        "metadata": {
            "title": "generic commune",
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
def invite(invited_user_id, community_id, role, inviter_token, invited_token):
    """Add/invite a user to a community with a specific role."""
    invitation_data = {
        "members": [{"type": "user", "id": invited_user_id}],
        "role": role,
        "message": "Welcome to the club!", #todo comment creation on invitation crashes due to trying to create comment on community record

    }

#    r = requests.get(
#        f"{BASE_URL}/api/communities/{community_id}/members",
#        headers=authorization_header(inviter_token),
#        verify=False
#    ).json()["hits"]["hits"]

    r = requests.post(
        f"{BASE_URL}/api/communities/{community_id}/invitations",
        headers=authorization_header(inviter_token),
        json=invitation_data,
        verify=False,
    )
    if not (r.status_code == 400 and r.json()["message"] == 'A member was already added or invited.'):
        assert r.status_code == 204
        time.sleep(1) #index refresh?
    elif r.status_code == 400 and r.json()["message"] == 'A member was already added or invited.':
        return

    invited_requests = requests.get(f"{BASE_URL}/api/user/requests", headers=authorization_header(invited_token), verify=False)
    request = _find_request_from_search_by_type(invited_requests, "community-invitation", topic={'community': community_id})
    accept = requests.post(request["links"]["actions"]["accept"], headers=authorization_header(invited_token), verify=False)
    assert accept.status_code == 200
    r = requests.get(
        f"{BASE_URL}/api/communities/{community_id}/members",
        headers=authorization_header(inviter_token),
        verify=False
    )
    return r
def publish_request_data(draft_id):
    return {'request_type': 'publish_draft', 'topic': {'documents_draft': draft_id}}

def get_community_from_results(result_response, slug):
    hits = result_response.json()["hits"]["hits"]
    for hit in hits:
        if hit["slug"] == slug:
            return hit
    return None
def create_or_get_community(creator_token, community_dict=None):
    if not community_dict:
        community_dict = COMMUNITY_DICT
    user_communities = requests.get(f"{BASE_URL}/api/user/communities?page=1&size=125", headers=authorization_header(creator_token), verify=False)
    existing_comm = get_community_from_results(user_communities, community_dict["slug"])
    if not existing_comm:
        comm = requests.post(f"{BASE_URL}/api/communities", headers=authorization_header(creator_token), json=community_dict, verify=False).json()
        print()
    else:
        comm = existing_comm
    comm = comm | {"custom_fields": {"workflow": "default"}}
    result = requests.put(f"{BASE_URL}/api/communities/{comm['id']}",
                  headers=authorization_header(creator_token), json=comm, verify=False)
    return comm

def invite_reader():
    """"""

def record_with_file(sample_record, token, community_id):
    resp_record = create_record_in_community(BASE_URL, sample_record, token=token, community_id=community_id, repo="docs")
    record_id = resp_record.json()["id"]
    upload_file(resp_record.json(), token)
    return requests.get(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(token), verify=False)

def create_published_record(sample_record, curator_token, community_id):
    resp_record = record_with_file(sample_record, curator_token, community_id)
    do_request(receiver_token=None, creator_token=curator_token, record_id=resp_record.json()["id"],
               type='publish_draft', is_draft=True, autoapprove=True)
    record_read = requests.get(f"{BASE_URL}/api/docs/{resp_record.json()['id']}", headers=authorization_header(curator_token), verify=False)
    return record_read

def create_draft(sample_record, curator_token, community_id):
    resp_record = record_with_file(sample_record, curator_token, community_id)
    return resp_record

def test_record_incomplete_data(submitter_token, curator_token, community_id):
    incomplete_sample_record = {"metadata": nrdocs_sample_matadata_missing_required_fields()}
    record1 = record_with_file(incomplete_sample_record, curator_token, community_id)
    #record2 = record_with_file(incomplete_sample_record, submitter_token, community_id)
    do_request(receiver_token=None, creator_token=curator_token, record_id=record1.json()["id"], type='publish_draft',
               is_draft=True, create_fail=True)
    #do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record2.json()["id"], type='publish_draft',
    #           is_draft=True, expected_status_code=400)

def _submit_request(request, creator_token, submit_forbidden):
    if submit_forbidden:
        assert "submit" not in request.json()["links"]["actions"]
        return request
    submit = requests.post(request.json()["links"]["actions"]["submit"],
                           headers=authorization_header(creator_token), verify=False)
    return submit

def _accept_request(submit_resp, receiver_token, autoapprove, expected_status_code):
    if not autoapprove:
        request_receiver = requests.get(f"{BASE_URL}/api/requests/{submit_resp.json()['id']}",
                                        headers=authorization_header(receiver_token), verify=False)
        accept = requests.post(request_receiver.json()["links"]["actions"]["accept"],
                               headers=authorization_header(receiver_token), verify=False)
        assert accept.status_code == expected_status_code
        return accept
    else:
        assert submit_resp.status_code == expected_status_code
        return submit_resp

# todo that deleted request crashes record accesibility might be a bug sometimes in future
def do_request(receiver_token, creator_token, record_id, type, payload=None, is_draft=False, create_forbidden=False,
               create_fail=False, submit_forbidden=False, autoapprove=False, expected_status_code=200, search_existing=False):
    record_url = f"{BASE_URL}/api/docs/{record_id}/draft?expand=true" if is_draft else f"{BASE_URL}/api/docs/{record_id}?expand=true"
    record_resp = requests.get(record_url, headers=authorization_header(creator_token), verify=False)
    #if record_resp.status_code == 410:
    #    return
    applicable_requests = requests.get(record_resp.json()["links"]["applicable-requests"], headers=authorization_header(creator_token), verify=False).json()["hits"]["hits"]
    if create_forbidden:
        request = _find_request_by_type_id(applicable_requests, type)
        assert request is None
        return

    if search_existing and not _find_request_by_type_id(applicable_requests, type): # the second condition bc we prefer to create new if possible
        rqs = requests.get(record_resp.json()["links"]["requests"],
                                       headers=authorization_header(creator_token), verify=False).json()["hits"]["hits"]
        rq = _find_request_by_type_id(rqs, type, custom_key="type") # type id searches applicable request types, type instatiated requests
        request = requests.get(rq["links"]["self"], headers=authorization_header(creator_token), verify=False)
        assert request.status_code == 200 #todo - the resolution of deleted request topic for event creation
        if request.json()["status"] == "created":
            request = _submit_request(request, creator_token, submit_forbidden)
        accept = _accept_request(request, receiver_token, False, expected_status_code)
        return accept

    else:
        request = create_request_on_record(applicable_requests, type, creator_token, data=payload)
        if create_fail:
            assert request.status_code == 400
            return
        assert request.status_code == 201
    submit = _submit_request(request, creator_token, submit_forbidden)
    accept = _accept_request(submit, receiver_token, autoapprove, expected_status_code)
    return accept


def change_workflow_test(token, community_id, community_data):
    # todo expand once there are more workflows in docs
    result_default = requests.put(f"{BASE_URL}/api/communities/{community_id}",
                                  headers=authorization_header(token), json=community_data|{"custom_fields": {"workflow": "default"}}, verify=False)
    result_nonexistent = requests.put(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(token),
                          json=community_data | {"custom_fields": {"workflow": "nonexistent"}}, verify=False)
    #non_existing_workflow_create = create_record_in_community(BASE_URL, sample_record, token, community_id, repo="docs")
    #assert non_existing_workflow_create.status_code == 400
    #backchange = requests.put(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(token), json=community_data["data"]|{"custom_fields": {"workflow": "default"}}, verify=False)
    #r = create_record_in_community(BASE_URL, sample_record, token, community_id, repo="docs")
    assert result_default.status_code == 200
    assert result_nonexistent.status_code == 400
    return

"""
def test_list_files()
"""

def edit_test(sample_record, token, community_id):
    record = create_published_record(sample_record, token, community_id)
    record_id = record.json()["id"]
    new_draft_direct = requests.post(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(token),
                             verify=False)
    assert new_draft_direct.status_code == 403
    do_request(receiver_token=None, creator_token=token, record_id=record_id, type='edit_published_record', autoapprove=True)
    new_draft = requests.get(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(token), verify=False)
    assert new_draft.status_code == 200
    new_data = new_draft.json()
    new_data["metadata"]["title"] = "new title"
    update = requests.put(f"{BASE_URL}/api/docs/{record_id}/draft", headers=authorization_header(token),
                          json=new_data, verify=False)
    do_request(receiver_token=None, creator_token=token, record_id=record_id, type='publish_changed_metadata',
               is_draft=True, autoapprove=True)
    published = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(token), verify=False)
    assert published.json()["metadata"]["title"] == "new title"

def new_version_test(sample_record, token, community_id):
    record = create_published_record(sample_record, token, community_id)
    record_id = record.json()["id"]
    new_version_direct = requests.post(f"{BASE_URL}/api/docs/{record_id}/versions", headers=authorization_header(token),
                             verify=False)
    assert new_version_direct.status_code == 403
    do_request(receiver_token=None, creator_token=token, record_id=record_id, type='new_version',
               autoapprove=True)
    time.sleep(5)
    # it would be cool if there was an api way to also read drafts by parent
    user_results = requests.get(f"{BASE_URL}/api/user/docs", headers=authorization_header(token), verify=False).json()["hits"]["hits"]
    parent_id = record.json()["parent"]["id"]
    results = [r for r in user_results if r["parent"]["id"] == parent_id]
    assert len(results) == 2

def doi_test(sample_record, curator_token, submitter_token, community_id):
    draft = create_record(BASE_URL, sample_record | {"parent": {"communities": {"default": community_id}}},
                                    submitter_token)
    draft = requests.get(f"{BASE_URL}/api/docs/{draft.json()['id']}/draft?expand=true", headers=authorization_header(submitter_token), verify=False)
    request_types = draft.json()["expanded"]["request_types"]

    #create_doi = _find_request_by_type_id(request_types, "create_doi")
    #edit_doi = _find_request_by_type_id(request_types, "edit_doi")

    request = create_request_on_record(draft, "create_doi", submitter_token)
    submit = requests.post(request.json()["links"]["actions"]["submit"],
                           headers=authorization_header(submitter_token), verify=False)
    request_receiver = requests.get(f"{BASE_URL}/api/requests/{submit.json()['id']}",
                                    headers=authorization_header(curator_token), verify=False)
    print()



def decline_request(record_id, token, request_type, is_draft=True):
    url = f"{BASE_URL}/api/docs/{record_id}/draft?expand=true" if is_draft else f"{BASE_URL}/api/docs/{record_id}?expand=true"
    reqs = requests.get(url, headers=authorization_header(token),
                          verify=False).json()["expanded"]["requests"]
    request_l = [r for r in reqs if r["type"] == request_type and r["is_open"] == True]
    if not request_l:
        print("no request found!!")
        return
    request = request_l[0]
    if "decline" in request["links"]["actions"]:
        return requests.post(request["links"]["actions"]["decline"], headers=authorization_header(token), verify=False)
    elif "cancel" in request["links"]["actions"]:
        return requests.post(request["links"]["actions"]["cancel"], headers=authorization_header(token), verify=False)
    raise Exception("no valid action to delete inactivate request")

def cleanup(owner_token, curator_token, *tokens):
    for token in (owner_token, curator_token, *tokens):
        records = requests.get(f"{BASE_URL}/api/user/docs?size=1000", headers=authorization_header(token),
                                        verify=False).json()["hits"]["hits"]
        for record in records:
            if record['state'] == "draft":
                res = requests.delete(f"{BASE_URL}/api/docs/{record['id']}/draft", headers=authorization_header(token),
                                        verify=False)
            elif record['state'] == "submitted":
                decl = decline_request(record['id'], curator_token, "publish_draft") # for noe curator is always receiver
                res = requests.delete(f"{BASE_URL}/api/docs/{record['id']}/draft", headers=authorization_header(token),
                                        verify=False)
            elif record['state'] in {"published", "retracting"}:
                decl = decline_request(record['id'], curator_token, "delete_published_record", is_draft=False)
                res = do_request(receiver_token=owner_token, creator_token=owner_token, record_id=record['id'],
                           type='delete_published_record', autoapprove=True, search_existing=True,
                                 payload = {"payload": {"removal_reason": "lalala your shit is gone tralala"}})
                print(res.status_code)
                """
                    do_request(receiver_token=curator_token, creator_token=owner_token, record_id=record_to_be_published_id,
               type='delete_published_record', payload = {"payload": {"removal_reason": "lalala your shit is gone tralala"}})
                """
                print()

            else:
                print("WEIRD RECORD STATE! could not delete") # todo record status should be serialized?
        time.sleep(5)
        records = requests.get(f"{BASE_URL}/api/user/docs?size=1000", headers=authorization_header(token),
                                        verify=False).json()["hits"]["hits"]
        assert len(records) == 0

def test_search(curator_token, submitter_token, community_id):
    # at this point - submitter has one published and two drafts, curator has a draft
    # submitter can read his own records
    # curator can read all records
    # to test correct query filter; we would have to use community role based approach to published records
    resp_sub_search = requests.get(f"{BASE_URL}/api/docs", headers=authorization_header(submitter_token),
                               verify=False).json()["hits"]["hits"]
    print()
    resp_sub_user_search = requests.get(f"{BASE_URL}/api/user/docs", headers=authorization_header(submitter_token),
                               verify=False).json()["hits"]["hits"]

    resp_curator_search = requests.get(f"{BASE_URL}/api/docs", headers=authorization_header(curator_token),
                               verify=False).json()["hits"]["hits"]
    resp_curator_user_search = requests.get(f"{BASE_URL}/api/user/docs", headers=authorization_header(curator_token),
                               verify=False).json()["hits"]["hits"]

    resp_sub_user_community_search = requests.get(f"{BASE_URL}/api/communities/{community_id}/user/docs",
                                                  headers=authorization_header(submitter_token),
                               verify=False).json()["hits"]["hits"]

    assert len(resp_sub_search) == 1
    assert len(resp_sub_user_search) == 3
    assert len(resp_curator_search) == 1
    assert len(resp_curator_user_search) == 1
    assert len(resp_sub_user_community_search) == 2

def test_community_members(owner_token, curator_token, submitter_token, *args, **kwargs):
    sample_record = {"metadata": nrdocs_sample_metadata()}

    community_id = create_or_get_community(owner_token)["id"]
    invite('2', community_id, "curator", owner_token, curator_token)
    invite('3', community_id, "submitter", owner_token, submitter_token)
    community2_id = create_or_get_community(owner_token, community_dict=COMMUNITY_DICT2)["id"]
    invite('2', community2_id, "curator", owner_token, curator_token)
    invite('3', community2_id, "submitter", owner_token, submitter_token)
    community3_id = create_or_get_community(owner_token, community_dict=COMMUNITY_DICT3)["id"]
    invite('2', community3_id, "curator", owner_token, curator_token)
    invite('3', community3_id, "submitter", owner_token, submitter_token)

    draft_submitter = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community_id}}}, submitter_token)

    delete_data = {
        "members": [{"type": "user", "id": '3'}],
    }
    member_delete = requests.delete(f"{BASE_URL}/api/communities/{community_id}/members", json=delete_data,
                                    headers=authorization_header(owner_token), verify=False)
    assert member_delete.status_code == 204

    print()
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=draft_submitter.json()["id"],
               type='publish_draft', is_draft=True, create_forbidden=True)

def init_communities(owner_token, curator_token, submitter_token):
    communities = requests.get(f"{BASE_URL}/api/communities?size=1000", headers=authorization_header(owner_token), verify=False).json()
    ret = {com_dct["slug"]: com_dct["id"] for com_dct in communities["hits"]["hits"]}
    return ret["generic"], ret["pilsencommune"], ret["brnocommune"]

def init_random_communities(owner_token, curator_token, submitter_token, n):
    def community_dict(i):
        return {
        "access": {
            "visibility": "public",
            "record_policy": "open",
        },
        "slug": f"generic_{i}",
        "metadata": {
            "title": f"generic commune {i}",
        },
    }

    for i in range(n):
        print(i)
        community_id = create_or_get_community(owner_token, community_dict=community_dict(i))["id"]
        invite('2', community_id, "curator", owner_token, curator_token)
        invite('3', community_id, "submitter", owner_token, submitter_token)

def init_benchmark_communities(owner_token, curator_token, submitter_token, n=100):
    init_random_communities(owner_token, curator_token, submitter_token, 100)

def benchmark(owner_token, curator_token, submitter_token):
    """
    cleanup(curator_token, submitter_token)
    t0 = time.time()

    for i in range(50):
        print(f"cur round {i}")
        sample_record = {"metadata": nrdocs_sample_metadata()}
        draft_curator = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": "generic_1"}}}, curator_token)
        draft_id = draft_curator.json()["id"]
        upload_file(draft_curator.json(), curator_token)
        do_request(receiver_token=curator_token,
                   creator_token=curator_token,
                   record_id=draft_id,
                   payload={"payload": {"version": "1.0"}},
                   type='publish_draft',
                   is_draft=True,
                   autoapprove=True)
    """


    t1 = time.time()
    for i in range(10):
        print(f"cur search round {i}")
        result = requests.get(f"{BASE_URL}/api/docs", headers=authorization_header(owner_token), verify=False).json()
        assert len(result["hits"]["hits"]) > 1
    t2 = time.time()
    # print(f"time required: {t1 - t0}")
    print(f"search time required: {t2 - t1}")

# with link permission checks:
# time required: 198.34403657913208
# search time required: 41.09484004974365

# without
# time required: 143.4331409931183
# search time required: 7.092546463012695

# only self, self_html
# time required: 192.4700345993042
# search time required: 10.73225736618042


def script_draft_to_publish(owner_token, curator_token, submitter_token, *args, **kwargs):
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    cleanup(owner_token, curator_token, submitter_token)

    record_with_file({"metadata": nrdocs_sample_metadata()}, submitter_token, community_id)
    """
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    cleanup(curator_token, submitter_token)

    sample_record = {"metadata": nrdocs_sample_metadata()}
    draft_curator = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community_id}}}, curator_token)
    draft_id = draft_curator.json()["id"]
    upload_file(draft_curator.json(), curator_token)


    do_request(receiver_token=curator_token,
               creator_token=curator_token,
               record_id=draft_id,
               payload={"payload": {"version": "1.0"}},
               type='publish_draft',
               is_draft=True,
               autoapprove=True)
    read_record(owner_token, curator_token, submitter_token, *args, **kwargs)
    print()
    """

def read_record(owner_token, curator_token, submitter_token, *args, **kwargs):
    search = requests.get(f"{BASE_URL}/api/docs", headers=authorization_header(owner_token), verify=False).json()["hits"]["hits"]

    read_response = requests.get(search[0]["links"]["self"], headers=authorization_header(owner_token), verify=False).json()
    read_response_expanded = requests.get(f"{search[0]['links']['self']}?expand=true", headers=authorization_header(owner_token), verify=False).json()
    print()

def published_record(submitter_token, curator_token, community_id, data=None, autoapprove=False):
    sample_record = {"metadata": nrdocs_sample_metadata()} if not data else data
    record_to_be_published = create_record_in_community(BASE_URL, sample_record,
                                                        token=submitter_token, community_id=community_id, repo="docs")
    record_to_be_published_id = record_to_be_published.json()["id"]
    upload_file(record_to_be_published.json(), submitter_token)
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record_to_be_published_id,
               type='publish_draft', is_draft=True, autoapprove=autoapprove)
    published_read = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published_id}",
                                  headers=authorization_header(curator_token), verify=False)
    return published_read

def test_edit_permission(owner_token, curator_token, submitter_token, *args, **kwargs):
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    cleanup(owner_token, curator_token, submitter_token)

    sample_record = {"metadata": nrdocs_sample_metadata()}
    record_to_be_published = create_record_in_community(BASE_URL, sample_record,
                                                        token=submitter_token, community_id=community_id, repo="docs")
    record_to_be_published_id = record_to_be_published.json()["id"]
    upload_file(record_to_be_published.json(), submitter_token)

    rs = requests.get(record_to_be_published.json()["links"]["applicable-requests"], headers=authorization_header(submitter_token),
                      verify=False).json()["hits"]["hits"]
    print()

    #published = published_record(submitter_token, curator_token, community_id)
    #record = published.json()
    #rs = requests.get(record["links"]["applicable-requests"], headers=authorization_header(submitter_token), verify=False).json()["hits"]["hits"]
    #edit_link = _find_request_by_type_id(rs, "edit_published_record")
    #edit_response = requests.post(edit_link["links"]["actions"]["create"], headers=authorization_header(submitter_token), verify=False)
    #rs_after = requests.get(record["links"]["applicable-requests"], headers=authorization_header(submitter_token), verify=False).json()["hits"]["hits"]
    #print()

def script_uploaded_published_record(owner_token, curator_token, submitter_token, *args, **kwargs):
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    cleanup(owner_token, curator_token, submitter_token)

    published = published_record(submitter_token, curator_token, community_id)

def script_test_new_version_files(owner_token, curator_token, submitter_token, *args, **kwargs):
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    cleanup(owner_token, curator_token, submitter_token)

    published = published_record(submitter_token, curator_token, community_id)

    result = do_request(receiver_token=None, creator_token=submitter_token, record_id=published.json()["id"], type='new_version',
               autoapprove=True, payload = {"payload": {"keep_files": "true"}})
    topic_files_link = result.json()["links"]["topic"]["files"]
    topic_files = requests.get(topic_files_link, headers=authorization_header(submitter_token), verify=False).json()
    assert len(topic_files["entries"]) > 0

def script_embargo_lift(owner_token, curator_token, submitter_token, *args, **kwargs):
    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)
    today = arrow.utcnow().shift(days=1).date().isoformat()
    sample_record = {"metadata": nrdocs_sample_metadata(), "access": {
        "record": "public",
        "files": "restricted",
        "status": "embargoed",
        "embargo": dict(active=True, until=today, reason=None),
    }}
    record_to_be_published = create_record_in_community(BASE_URL, sample_record, token=submitter_token, community_id=community_id, repo="docs")
    upload_file(record_to_be_published.json(), submitter_token)
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record_to_be_published.json()["id"],
               type='publish_draft', is_draft=True)
    record_files = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}/files"
                                       , headers=authorization_header(curator_token), verify=False)  #should be embargoed
    time.sleep(240)
    record_files_after_lift = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}/files"
                                       , headers=authorization_header(curator_token), verify=False)
    assert record_files.status_code == 403
    assert record_files_after_lift.status_code == 200

def script_contributor_serialization(owner_token, curator_token, submitter_token, *args, **kwargs):
    sample_record = {"metadata": nrdocs_sample_metadata()}
    sample_record_with_url = {"metadata": nrdocs_sample_metadata_custom("sample_record_affiliations_wurl.json")}

    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)

    #record2
    record_to_be_published = create_record_in_community(BASE_URL, sample_record_with_url, token=submitter_token, community_id=community_id, repo="docs")
    errors = {error["field"] for error in record_to_be_published.json()["errors"]}

    """
    {'metadata.accessRights', 
    'metadata.contributors.1.affiliations.0.@v', 
    'metadata.contributors.1.affiliations.0.hierarchy', 
    'metadata.contributors.1.affiliations.0.title', 
    'metadata.contributors.1.person_or_org.identifiers.0.url'}
    """
    assert 'metadata.contributors.1.person_or_org.identifiers.0.url' in errors #not crashing now
    upload_file(record_to_be_published.json(), submitter_token)
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record_to_be_published.json()["id"],
               type='publish_draft', is_draft=True)
    published_read = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}",
                                  headers=authorization_header(curator_token), verify=False).json()
    published_read_ui = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}",
                                  headers=authorization_header(curator_token) | ui_serialization_header(), verify=False).json()
    assert "url" not in published_read['metadata']['contributors'][1]['person_or_org']['identifiers'][0]
    assert published_read_ui['metadata']['contributors'][1]['person_or_org']['identifiers'][0]["url"] == 'https://orcid.org/0000-0002-1825-0097'

    #record1
    record_to_be_published = create_record_in_community(BASE_URL, sample_record, token=submitter_token, community_id=community_id, repo="docs")
    upload_file(record_to_be_published.json(), submitter_token)
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record_to_be_published.json()["id"],
               type='publish_draft', is_draft=True)
    published_read = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}",
                                  headers=authorization_header(curator_token), verify=False).json()
    published_read_ui = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}",
                                  headers=authorization_header(curator_token) | ui_serialization_header(), verify=False).json()
    assert "url" not in published_read['metadata']['contributors'][1]['person_or_org']['identifiers'][0]
    assert published_read_ui['metadata']['contributors'][1]['person_or_org']['identifiers'][0]["url"] == 'https://orcid.org/0000-0002-1825-0097'


def script(owner_token, curator_token, submitter_token, *args, **kwargs):
    sample_record = {"metadata": nrdocs_sample_metadata()}

    community_id, community2_id, community3_id = init_communities(owner_token, curator_token, submitter_token)


    cleanup(owner_token, curator_token, submitter_token) # there's no method to search different users drafts
    #doi_test(sample_record, curator_token, submitter_token, community_id)
    #sys.exit()


    # create is temporarily auth user
    # test direct create disabled
    record_resp = create_record(BASE_URL, sample_record, submitter_token)
    assert record_resp.status_code == 400
    # test direct create in community allowed
    draft_submitter = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community_id}}}, submitter_token) # test creation through invenio endpoint
    draft_submitter_community2 = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community2_id}}}, submitter_token)
    draft_curator = create_record(BASE_URL, sample_record|{"parent":{"communities": {"default": community_id}}}, curator_token)
    assert draft_submitter.status_code == 201
    assert draft_submitter_community2.status_code == 201
    assert draft_curator.status_code == 201

    change_workflow_test(owner_token, community_id, requests.get(f"{BASE_URL}/api/communities/{community_id}", headers=authorization_header(owner_token), verify=False).json())

    record_to_be_published = create_record_in_community(BASE_URL, sample_record, token=submitter_token, community_id=community_id, repo="docs")
    assert record_to_be_published.status_code == 201
    record_to_be_published_id = record_to_be_published.json()["id"]
    upload_file(record_to_be_published.json(), submitter_token)


    time.sleep(10)
    anonymous_files_on_draft_list = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}/draft/files", verify=False)
    files_on_draft_list = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published.json()['id']}/draft/files"
                                       , headers=authorization_header(submitter_token), verify=False)
    assert anonymous_files_on_draft_list.status_code == 403
    assert files_on_draft_list.status_code == 200

    #only owner is also record owner and curator is allowed
    do_request(receiver_token=curator_token, creator_token=submitter_token, record_id=record_to_be_published_id,
               type='publish_draft', is_draft=True)
    published_read = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published_id}",
                                  headers=authorization_header(curator_token), verify=False)
    assert published_read.status_code == 200
    record_id = published_read.json()["id"]

    time.sleep(5)
    test_search(curator_token, submitter_token, community_id)

    record_published_by_autoapprove = create_record_in_community(BASE_URL, sample_record, token=submitter_token, community_id=community_id, repo="docs")
    record_published_by_autoapprove_id = record_published_by_autoapprove.json()["id"]
    upload_file(record_published_by_autoapprove.json(), submitter_token)
    time.sleep(2)
    do_request(receiver_token=None, creator_token=curator_token, record_id=record_published_by_autoapprove_id, type='publish_draft', is_draft=True, autoapprove=True) # publish record by curator is autoapproved
    record_published_by_autoapprove = requests.get(f"{BASE_URL}/api/docs/{record_published_by_autoapprove_id}", headers=authorization_header(curator_token), verify=False)
    assert record_published_by_autoapprove.status_code == 200 # test if the record is published without explicit approve

    #test_record_incomplete_data(submitter_token, curator_token, community_id)

    #test submit secondary
    time.sleep(2)
    payload = {'payload': {'community': community2_id}}
    do_request(receiver_token=owner_token, creator_token=curator_token, record_id=record_id,
               type="secondary_community_submission", payload=payload, autoapprove=True)

    #test migrate
    payload = {'payload': {'community': community3_id}}
    init = do_request(receiver_token=owner_token, creator_token=curator_token, record_id=record_id,
               type="initiate_community_migration", payload=payload, autoapprove=True)
    request = [r for r in requests.get(f"{BASE_URL}/api/requests", headers=authorization_header(owner_token), verify=False).json()["hits"]["hits"] if r["type"]=="confirm_community_migration" and r["is_open"]==True and r["topic"]=={'documents': record_id}][0]
    request_resp = requests.get(f"{BASE_URL}/api/requests/{request['id']}", headers=authorization_header(owner_token), verify=False)
    _accept_request(request_resp, curator_token, False, 200)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(curator_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community2_id, community3_id}
    assert record_communities["default"] == community3_id

    # todo global search service bug - thesis service added twice from eps!!
    # should be docs instead of documents i guess
    # record_communities_search = requests.get(f"{BASE_URL}/api/docs/{record_id}/communities", headers=authorization_header(curator_token), verify=False)
    community_records = requests.get(f"{BASE_URL}/api/communities/{community_id}/records", headers=authorization_header(curator_token), verify=False)
    # assert record_communities_search.status_code == 200
    # assert len(record_communities_search.json()["hits"]["hits"]) == 2
    assert community_records.status_code == 200

    #test remove secondary
    """ # not implemented yet
    payload = {'payload': {'community': community2_id}}
    do_request(owner_token, curator_token, record_id, "remove_secondary_community", payload)

    time.sleep(2)
    record = requests.get(f"{BASE_URL}/api/docs/{record_id}", headers=authorization_header(curator_token), verify=False).json()
    record_communities = record["parent"]["communities"]
    assert set(record_communities["ids"]) == {community3_id}
    """
    # test edit autoapprove

    edit_test(sample_record, curator_token, community_id)
    new_version_test(sample_record, curator_token, community_id)


    #test delete record
    delete_directly = requests.delete(f"{BASE_URL}/api/docs/{record_to_be_published_id}", headers=authorization_header(owner_token), verify=False)
    assert delete_directly.status_code == 403

    do_request(receiver_token=None, creator_token=owner_token, record_id=record_to_be_published_id,
               type='delete_published_record', autoapprove=True, payload = {"payload": {"removal_reason": "lalala your shit is gone tralala"}})
    time.sleep(2)
    record_resp = requests.get(f"{BASE_URL}/api/docs/{record_to_be_published_id}",
                               headers=authorization_header(curator_token), verify=False)
    assert record_resp.status_code == 404