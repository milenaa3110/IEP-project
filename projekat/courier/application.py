import datetime
import json
import re
import io
import csv

from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, Product, ProductOrder, ProductCategory, Order, Category
from email.utils import parseaddr
from sqlalchemy.orm import session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity
from sqlalchemy import and_
from roleCheckDecorator  import roleCheck
from flask_jwt_extended import JWTManager
from web3 import Web3, Account
from web3.exceptions import ContractLogicError
def jsonResponse(message, status):
    responseData = {}
    responseData["message"] = message
    return Response(json.dumps(responseData), status = status)

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)
w3 = Web3(Web3.HTTPProvider('http://ganache:8545'))


@application.route("/orders_to_deliver", methods=["GET"])
@roleCheck("courier")
def orderToDeliver():
    orders = Order.query.filter_by(status="CREATED")
    resultObj = {}
    resultObj["orders"] = [
        {
            "id": order.id,
            "email": order.email
        }
        for order in orders
    ]
    return Response(json.dumps(resultObj, indent=4, sort_keys=True, default=str), status=200)

@application.route("/pick_up_order", methods=["POST"])
@roleCheck("courier")
def pickUpOrder():
    try:
        requestObject = request.get_json()
        if "id" not in requestObject.keys():
            return jsonResponse("Missing order id.", 400)
        id = requestObject["id"]
        if not isinstance(id, int) or id < 0:
            return jsonResponse("Invalid order id.", 400)
        order = Order.query.filter_by(status="CREATED", id=id).first()
        if order is None:
            return jsonResponse("Invalid order id.", 400)
        if "address" not in requestObject.keys() or requestObject["address"]=="":
            return jsonResponse("Missing address.", 400)
        if not Web3.is_address(requestObject["address"]):
            return jsonResponse("Invalid address.", 400)
        with open("output/OrderContract.abi", "r") as file:
            contract_abi = json.load(file)
        courier_address = requestObject["address"]
        contract = w3.eth.contract(address=order.address, abi=contract_abi)
        if contract.functions.status().call()!=1:
            return jsonResponse("Transfer not complete.", 400)
        if contract.functions.courier().call() != "0x0000000000000000000000000000000000000000":
            return jsonResponse(f"Delivery not complete.", 400)
        with open("/data/keyfile.json", 'r') as file:
            encrypted_key_data = json.load(file)

            decrypted_key = Account.decrypt(encrypted_key_data, "iep-project")
            owner_address = Account.from_key(decrypted_key).address

        try:
            transaction = contract.functions.setCourier(courier_address).build_transaction({
                'gas': 2000000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(owner_address),
                'value': 0
            })
            signed_txn = w3.eth.account.sign_transaction(transaction, decrypted_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            return jsonResponse(str(e), 400)
        order.status = "PENDING"
        database.session.commit()
        return jsonResponse("", 200)
    except Exception as e:
        return jsonResponse(str(e), 400)

if(__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port = 5003)