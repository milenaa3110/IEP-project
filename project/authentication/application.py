import json

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, User, Role
from email.utils import parseaddr
from sqlalchemy.orm import session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity
from sqlalchemy import and_
from roleCheckDecorator import roleCheck
from flask_jwt_extended import JWTManager
import re

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/", methods=["GET"])
def index():
    return "Hello world!"

def check_password(password):

    if len(password) < 8 or len(password) > 256:
        return False

    smallFlag = False
    bigFlag = False
    numFlag = False

    for char in password:
        if(str.islower(char)):
            smallFlag = True
        elif(str.isupper(char)):
            bigFlag = True
        elif(str.isdigit(char)):
            numFlag = True

    return smallFlag and bigFlag and numFlag

@application.route("/test", methods=["GET"])
def test():
    Roles = Role.query.all()
    string = ""
    for role in Roles:
        string += str(role.id) + "-" + str(role.name) + "\n"
    return  string

@application.route("/register_customer", methods=["POST"])
def register_customer():
    data = request.get_json()

    required_fields = ['forename', 'surname', 'email', 'password']

    responseData = {}
    responseData["message"] = ""

    # ERROR 400 response
    for field in required_fields:
        if field not in data or not data[field]:
            responseData = {"message": f"Field {field} is missing."}
            return Response(json.dumps(responseData), status=400)
    email = data.get('email')
    password = data.get('password')
    forename = data.get('forename')
    surname = data.get('surname')

    # email and password validation
    passwordInvalid = len(password) < 8 or len(password) > 256 or not check_password(password)

    emailCheck = User.query.filter(User.email == email).first()

    # email format validation
    if not re.match("[^@]+@[^@]+\.[^@]{2,}", email):
        responseData["message"] = "Invalid email."
        return Response(json.dumps(responseData), status=400)
    if (passwordInvalid):
        responseData["message"] = "Invalid password."
        return Response(json.dumps(responseData), status=400)
    if(emailCheck != None):
        responseData["message"] = "Email already exists."
        return Response(json.dumps(responseData), status=400)

    customerId = Role.query.filter(Role.name == "customer").first().id
    user = User( email = email,
                 password = password,
                 forename = forename,
                 surname = surname,
                 roleId =  customerId
     )
    database.session.add(user)
    database.session.commit()
    return Response("", status = 200)

@application.route("/register_courier", methods=["POST"])
def register_courier():
    data = request.get_json()

    required_fields = ['forename', 'surname', 'email', 'password']

    responseData = {}
    responseData["message"] = ""

    # ERROR 400 response
    for field in required_fields:
        if field not in data or not data[field]:
            responseData = {"message": f"Field {field} is missing."}
            return Response(json.dumps(responseData), status=400)

    email = data.get('email')
    password = data.get('password')
    forename = data.get('forename')
    surname = data.get('surname')

    # email and password validation
    passwordInvalid = len(password) < 8 or len(password) > 256 or not check_password(password)

    emailCheck = User.query.filter(User.email == email).first()

    # email format validation
    if not re.match("[^@]+@[^@]+\.[^@]{2,}", email):
        responseData["message"] = "Invalid email."
        return Response(json.dumps(responseData), status=400)
    if (passwordInvalid):
        responseData["message"] = "Invalid password."
        return Response(json.dumps(responseData), status=400)
    if(emailCheck != None):
        responseData["message"] = "Email already exists."
        return Response(json.dumps(responseData), status=400)

    courierId = Role.query.filter(Role.name == "courier").first().id
    user = User( email = email,
                 password = password,
                 forename = forename,
                 surname = surname,
                 roleId =  courierId
     )
    database.session.add(user)
    database.session.commit()
    return Response("", status = 200)

jwt = JWTManager(application)

@application.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    required_fields = ['email', 'password']

    responseData = {}
    responseData["message"] = ""

    for field in required_fields:
        if field not in data or not data[field]:
            responseData = {"message": f"Field {field} is missing."}
            return Response(json.dumps(responseData), status=400)

    email = data.get('email')
    password = data.get('password')

    # email format validation
    if not re.match("[^@]+@[^@]+\.[^@]{2,}", email):
        responseData["message"] = "Invalid email."
        return Response(json.dumps(responseData), status=400)

    # credentials check
    user = User.query.filter(and_(User.email == email, User.password == password)).first()
    if(not user):
        responseData["message"] = "Invalid credentials."
        return Response(json.dumps(responseData), status=400)

    # error status response
    if(len(responseData["message"]) > 0):
        return  Response(json.dumps(responseData), status=400)

    additionalClaims = {
        "forename": user.forename,
        "surname":  user.surname,
        "roles" : [user.role.name]
    }
    accessToken = create_access_token(identity=user.email, additional_claims= additionalClaims)
    refreshToken = create_refresh_token(identity=user.email, additional_claims= additionalClaims)
    return  jsonify(accessToken = accessToken, refreshToken = refreshToken)


@application.route("/refresh", methods=["POST"])
@jwt_required(refresh = True)
def refresh():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    additionalClaims = {
        "forename": refreshClaims["forename"],
        "surname": refreshClaims["surname"],
        "roles": refreshClaims["roles"],
    }
    responseData = {}
    responseData["accessToken"] =  create_access_token(identity= identity, additional_claims= additionalClaims)
    return Response(json.dumps(responseData), status = 200)

@application.route("/delete", methods=["POST"])
@jwt_required()
def delete():
    responseData = {}
    auth_header = request.headers.get('Authorization')
    if not auth_header or 'Bearer ' not in auth_header:
        responseData["msg"] = "Missing Authorization Header"
        return Response(json.dumps(responseData), status=401)

    token = get_jwt()
    email = token.get("sub")
    print(email)
    query = User.query.filter(User.email == email)

    if query.first() is None:
        responseData["message"] = f"Unknown user."
        return Response(json.dumps(responseData), status=400)
    query.delete()
    database.session.commit()
    return Response("", status=200)

if(__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port = 5000)