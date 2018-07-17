import numpy,re
from flask import Flask, jsonify, request
from pymongo import MongoClient

# Mongo Config
client = MongoClient('localhost', 27017)
db = client.friend_book
collection = db.Friends


app = Flask(__name__)

API_KEY = "UE133FKO340OF399A0023DD3421DAS21"

@app.route('/')
def hello_world():
    return jsonify(status = "okay")

@app.route('/create_user', methods=['POST'])
def create_user():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['first_name', 'last_name', 'email']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    user_email = req_json['email']

    result = collection.find_one({"email":user_email})

    if result is not None:
        return jsonify(status="error", msg="email already exist"), 401

    req_json.update({
        "friends":[],
        "subscriber":[],
        "subscribed":[],
        "blocked":[]
    })

    collection.insert_one(req_json)

    return jsonify(success="true")


@app.route('/connect' , methods=['POST'])
def connect_people():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status = "error", msg = "invalid api key"), 401

    REQUIRED_PARAMS = ['friends']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    friends = req_json['friends']

    requester = collection.find_one({"email": friends[0]})
    request_to = collection.find_one({"email": friends[1]})

    if requester is None:
        return jsonify(status="error", msg="user does not exist"), 401

    if request_to is None:
        return jsonify(status="error", msg="user does not exist"), 401

    blocked = collection.find({"email": requester, "blocked": request_to}).count()

    if blocked:
        return jsonify(status="success", msg="Contact is Blocked. Cannot connect to user."), 200

    collection.update_one({"email": friends[0]},
                          {"$addToSet": {"friends": friends[1]}})

    collection.update_one({"email": friends[1]},
                          {"$addToSet": {"friends": friends[0]}})

    return jsonify(success="true")

@app.route('/get_friends' , methods=['POST'])
def get_friends():

    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['email']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    user_email = req_json['email']

    result = collection.find_one({"email": user_email}, {"friends": 1})

    return jsonify(success="true",friends=result['friends'],count=len(result['friends']))

@app.route('/get_mutual_friends' , methods=['POST'])
def get_mutual_friends():

    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['friends']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    user_emails = req_json['friends']

    user_one = collection.find_one({"email": user_emails[0]}, {"friends": 1})
    user_two = collection.find_one({"email": user_emails[1]}, {"friends": 1})


    if user_one is not None and user_two is not None:
        result = numpy.intersect1d(user_one['friends'], user_two['friends']).tolist()
    else:
        result = []

    return jsonify(success="true",friends=result,count=len(result))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status = "error", msg = "invalid api key"), 401

    REQUIRED_PARAMS = ['requester', 'target']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    requester_email = req_json['requester']
    target_email = req_json['target']

    requester = collection.find_one({"email": requester_email})
    target = collection.find_one({"email": target_email})

    if requester is None:
        return jsonify(status="error", msg="user does not exist"), 401

    if target is None:
        return jsonify(status="error", msg="user does not exist"), 401

    blocked = collection.find({"email": requester_email, "blocked": target_email}).count()

    if blocked:
        return jsonify(status="success", msg="Contact is Blocked. Cannot connect to user."), 200

    collection.update_one({"email": requester_email},
                          {"$addToSet": {"subscribed": target_email}})

    collection.update_one({"email": target_email},
                          {"$addToSet": {"subscriber": requester_email}})

    return jsonify(success="true")

@app.route('/block_user', methods=['POST'])
def block_users():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['requester', 'target']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    requester_email = req_json['requester']
    target_email = req_json['target']

    requester = collection.find_one({"email": requester_email})
    target = collection.find_one({"email": target_email})

    if requester is None:
        return jsonify(status="error", msg="user does not exist"), 401

    if target is None:
        return jsonify(status="error", msg="user does not exist"), 401

    collection.update({"email": requester_email}, {"$pull": {"friends": target_email}})
    collection.update({"email": requester_email}, {"$pull": {"subscriber": target_email}})
    collection.update({"email": requester_email}, {"$pull": {"subscribed": target_email}})
    collection.update({"email": requester_email}, {"$addToSet": {"blocked": target_email}})
    collection.update({"email": target_email}, {"$pull": {"friends": requester_email}})
    collection.update({"email": target_email}, {"$pull": {"subscriber": requester_email}})
    collection.update({"email": target_email}, {"$pull": {"subscribed": requester_email}})
    collection.update({"email": target_email}, {"$addToSet": {"blocked": requester_email}})

    return jsonify(success="true")

@app.route('/unblock_user', methods=['POST'])
def unblock_users():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['requester', 'target']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    requester_email = req_json['requester']
    target_email = req_json['target']

    requester = collection.find_one({"email": requester_email})
    target = collection.find_one({"email": target_email})

    if requester is None:
        return jsonify(status="error", msg="user does not exist"), 401

    if target is None:
        return jsonify(status="error", msg="user does not exist"), 401

    collection.update({"email": requester_email}, {"$pull": {"blocked": target_email}})
    collection.update({"email": target_email}, {"$pull": {"blocked": requester_email}})

    return jsonify(success="true")

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['requester', 'target']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    requester_email = req_json['requester']
    target_email = req_json['target']

    requester = collection.find_one({"email": requester_email})
    target = collection.find_one({"email": target_email})

    if requester is None:
        return jsonify(status="error", msg="user does not exist"), 401

    if target is None:
        return jsonify(status="error", msg="user does not exist"), 401

    collection.update({"email": requester_email}, {"$pull": {"subscribed": target_email}})
    collection.update({"email": target_email}, {"$pull": {"subscriber": requester_email}})

    return jsonify(success="true")

@app.route('/updates_from_me', methods=['POST'])
def updates_from_me():
    api = request.headers['api-key']

    if api != API_KEY:
        return jsonify(status="error", msg="invalid api key"), 401

    REQUIRED_PARAMS = ['sender', 'text']

    req_json = request.get_json()

    for param in REQUIRED_PARAMS:
        if param not in req_json:
            return jsonify(status="error", msg="invalid param"), 401

    text = req_json['text']
    requester_email = req_json['sender']

    recipients = []

    emails_in_text = re.findall(r'[\w\.-]+@[\w\.-]+', text)

    for email in emails_in_text:
        blocked = collection.find({"email": requester_email,"blocked":email}).count()

        email_exist = collection.find_one({"email": email})

        if email_exist is not None:
            if not blocked:
                recipients.append(email)

    friends = collection.find_one({"email": requester_email},{"friends":1})
    subscriber = collection.find_one({"email": requester_email}, {"subscriber": 1})

    recipients = recipients + friends['friends'] + subscriber['subscriber']

    return jsonify(success="true",recipients=recipients)

if __name__ == '__main__':
    app.run()
