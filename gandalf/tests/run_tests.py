import urllib
import urllib2
import json

TEST_GANDALF_URL = "http://localhost:8080/gandalf/tests/run_step"

def test_response(step, data={}):
    global last_opener

    data["step"] = step

    req = urllib2.urlopen("%s?%s" % (TEST_GANDALF_URL, urllib.urlencode(data)))

    try:
        response = req.read()
    finally:
        req.close()

    return json.loads(response)

def run_tests():
    assert(test_response("can_cross_empty_bridge") == False)
    assert(test_response("can_cross_all_users_whitelist") == True)
    assert(test_response("can_cross_all_users_blacklist") == False)
    assert(test_response("can_cross_all_users_whitelist_and_blacklist") == False)

    # Try these a few times to make sure that users do not jump between
    # being inside or outside a percentage between requests
    for i in range(0, 5):
        assert(test_response("can_cross_all_users_inside_percentage") == True)
        assert(test_response("can_cross_all_users_outside_percentage") == False)

    print "Tests successful."

if __name__ == "__main__":
    run_tests()
