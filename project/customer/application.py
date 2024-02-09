import datetime
import json
import re
import io
import csv
import ast
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


@application.route("/search", methods=["GET"])
@roleCheck("customer")
def search():
    name = request.args.get("name", None)
    category = request.args.get("category", None)

    # all categories whose name matches the category parameter
    searchCategories = []
    if(category is None or len(category) == 0):
        searchCategories = Category.query.all()
    else:
        searchCategories = Category.query.filter(Category.name.like("%" + category + "%")).all()


    # all products whose name matches the name parameter
    searchProducts = []
    if (name is None or len(name) == 0):
        searchProducts = Product.query.all()
    else:
        searchProducts = Product.query.filter(Product.name.like("%" + name + "%")).all()


    # dictionaries used for cross-checking categories and products
    categoriesDict = {cat.id: {"obj": cat, "flag": False} for cat in searchCategories}
    productsDict = {prod.id :{"obj": prod, "flag": False} for prod in searchProducts}

    for product in searchProducts:
        for cat in product.categories:
            # if category has at least one product, flag will be set to true
            # if product belongs to at least one category, flag will be set to true
            if(cat.id in categoriesDict.keys()):
                categoriesDict[cat.id]["flag"] = True
                productsDict[product.id]["flag"] = True

    #extracting just the objects that have their flag set to True
    resultProducts = [x["obj"] for x in productsDict.values() if x["flag"] == True]
    resultCategories = [x["obj"] for x in categoriesDict.values() if x["flag"] == True]


    # formatting the JSON response in requested format
    resultObject = {}
    resultObject["categories"] = [cat.name for cat in resultCategories]
    resultObject["products"] = [
        {
        "categories" : [cat.name for cat in prod.categories],
        "id" : prod.id,
        "name": prod.name,
        "price": prod.price,
        }
        for prod in resultProducts ]

    return Response(json.dumps(resultObject), status= 200)


@application.route("/order", methods=["POST"])
@roleCheck("customer")
def order():
    requestObject =  request.get_json()
    if "requests" not in requestObject.keys():
        return jsonResponse("Field requests is missing.", 400)

    requests = requestObject["requests"]

    for index, req in enumerate(requests):
        if "id" not in req.keys():
             return jsonResponse("Product id is missing for request number " + str(index) + ".", 400)
        if "quantity" not in req.keys():
            return jsonResponse("Product quantity is missing for request number " + str(index) + ".", 400)
        if not isinstance(req["id"], int) or req["id"] < 0:
            return jsonResponse("Invalid product id for request number " + str(index) + ".", 400)
        if not isinstance(req["quantity"], int) or req["quantity"] < 0:
            return jsonResponse("Invalid product quantity for request number " + str(index) + ".", 400)
        if Product.query.filter(Product.id == req["id"]).first() is None:
            return jsonResponse("Invalid product for request number " + str(index) + ".", 400)
    if "address" not in requestObject.keys() or requestObject["address"]=="":
        return jsonResponse("Field address is missing.", 400)
    if not Web3.is_address(requestObject["address"]):
        return jsonResponse("Invalid address.", 400)

    with open("output/OrderContract.abi", "r") as file:
        contract_abi = json.load(file)

    with open("output/OrderContract.bin", "r") as file:
        contract_bytecode = file.read()
    contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

    with open("/data/keyfile.json", 'r') as file:
        encrypted_key_data = json.load(file)

    decrypted_key = Account.decrypt(encrypted_key_data, "iep-project")

    address = requestObject["address"]
    deploy_address = Account.from_key(decrypted_key).address


    user_email = get_jwt_identity()
    order = Order(timestamp=datetime.datetime.now(),
                  status="CREATED",
                  price=0,
                  email=user_email,
                  address=deploy_address)
    database.session.add(order)
    database.session.commit()

    for req in requests:
        product = Product.query.filter(Product.id == req["id"]).first()
        order.price += product.price * req["quantity"]

        orderItem = ProductOrder(orderId = order.id,
                                 productId = product.id,
                                 quantity = req["quantity"],
                                 price = product.price)

        database.session.add(product)
        database.session.add(orderItem)
        database.session.commit()
    estimated_gas = contract.constructor(address, w3.to_wei('1', 'ether')).estimate_gas({
        'from': deploy_address
    })

    transaction = contract.constructor(address, w3.to_wei(order.price*0.00062 , 'ether')).build_transaction({
        'from': deploy_address,
        'nonce': w3.eth.get_transaction_count(deploy_address),
        'gas': int(estimated_gas * 1.2),  # adding 20% buffer
        'gasPrice': w3.eth.gas_price
    })

    signed_transaction = w3.eth.account.sign_transaction(transaction, decrypted_key)
    tx_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Ako je transakcija uspešna, ugovor je postavljen na mrežu
    contract_address = tx_receipt['contractAddress']
    order.address = contract_address
    database.session.commit()
    responseData = {}
    responseData["id"] = order.id

    return Response(json.dumps(responseData), 200)

@application.route("/status", methods=["GET"])
@roleCheck("customer")
def status():

    orders = Order.query.all()

    resultObj = {}
    resultObj["orders"] = [
        {
            # array of Product and ProductOrder data
            "products": [
                {
                    "categories": [cat.name for cat in item.product.categories],
                    "name": item.product.name,
                    "price": ProductOrder.query.filter_by(productId=item.product.id, orderId=order.id).first().price,
                    "quantity":  ProductOrder.query.filter_by(productId=item.product.id, orderId=order.id).first().quantity
                }
                for item in order.orderItems],
            "price": order.price,
            "status": order.status,
            "timestamp": order.timestamp

        }
        for order in orders
    ]
    return Response(json.dumps(resultObj, indent=4, sort_keys=True, default=str), status=200)


def fix_quotes(s):
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(s)
        except:
            raise ValueError("Unable to parse the provided string")
    return json.dumps(data)

@application.route("/delivered", methods=["POST"])
@roleCheck("customer")
def delivered():
    try:
        requestObject = request.get_json()
        if "id" not in requestObject.keys():
            return jsonResponse("Missing order id.", 400)
        id = requestObject["id"]
        if not isinstance(id, int) or id < 0:
            return jsonResponse("Invalid order id.", 400)
        order = Order.query.filter_by(status="PENDING", id=id).first()
        if order is None:
            return jsonResponse("Invalid order id.", 400)
        if "keys" not in requestObject.keys() or requestObject["keys"]=="" :
            return jsonResponse("Missing keys.", 400)
        if "passphrase" not in requestObject.keys() or requestObject["passphrase"]=="":
            return jsonResponse("Missing passphrase.", 400)
        keys = fix_quotes(requestObject["keys"])
        try:
            decrypted_key = Account.decrypt(keys, requestObject["passphrase"])
            account = Account.from_key(decrypted_key)
            customer_address = account.address
        except:
            return jsonResponse("Invalid credentials.", 400)
        with open("output/OrderContract.abi", "r") as file:
            contract_abi = json.load(file)

        contract = w3.eth.contract(address=order.address, abi=contract_abi)
        contract_status = contract.functions.status().call()
        if contract.functions.customer().call() != customer_address:
            return jsonResponse("Invalid customer account.", 400)
        if contract_status == 0:
            return jsonResponse("Transfer not complete.", 400)
        if contract_status != 2:
            return jsonResponse("Delivery not complete.", 400)
        customer_address = w3.to_checksum_address(customer_address)
        try:
            tx = contract.functions.confirmDelivery().build_transaction({
                'nonce': w3.eth.get_transaction_count(customer_address),
                'gasPrice': w3.eth.gas_price,
                'gas': 2000000,
                'value': 0,
            })
            signed_txn = w3.eth.account.sign_transaction(tx, decrypted_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        except ContractLogicError as e:
            error_message = str(e)
            return jsonResponse(error_message, 400)

        order.status = "COMPLETE"
        database.session.commit()
        return jsonResponse("", 200)
    except Exception as e:
        error_message = str(e)
        return jsonResponse(error_message, 400)

@application.route("/pay", methods=["POST"])
@roleCheck("customer")
def pay():
    requestObject = request.get_json()
    if "id" not in requestObject.keys():
        return jsonResponse("Missing order id.", 400)
    id = requestObject["id"]
    if not isinstance(id, int) or id < 0:
        return jsonResponse("Invalid order id.", 400)
    order = Order.query.filter_by(id=id).first()
    if order is None:
        return jsonResponse("Invalid order id.", 400)
    if "keys" not in requestObject.keys() or requestObject["keys"] == "":
        return jsonResponse("Missing keys.", 400)
    if "passphrase" not in requestObject.keys() or requestObject["passphrase"] == "":
        return jsonResponse("Missing passphrase.", 400)
    keys = requestObject["keys"]
    try:
        keys_dict = json.loads(keys)
        decrypted_key = Account.decrypt(keys_dict, requestObject["passphrase"])
        account = Account.from_key(decrypted_key)
        customer_address = account.address
    except:
        return jsonResponse("Invalid credentials.", 400)
    try:
        with open("output/OrderContract.abi", "r") as file:
            contract_abi = json.load(file)

        contract = w3.eth.contract(address=order.address, abi=contract_abi)
        if contract.functions.status().call() != 0:
            return jsonResponse("Transfer already complete.", 400)
        balance = w3.eth.get_balance(customer_address)
        order_price = contract.functions.orderPrice().call()
        estimated_gas = contract.functions.makePayment().estimate_gas({'from': customer_address, 'value': order_price})
        gas_price = w3.eth.gas_price
        estimated_transaction_cost = estimated_gas * gas_price + order_price

        # Check if the balance is sufficient
        if balance < estimated_transaction_cost:
            return jsonResponse(f"Insufficient funds", 400)

        try:
            tx = contract.functions.makePayment().build_transaction({
                'nonce': w3.eth.get_transaction_count(customer_address),
                'gasPrice': gas_price,
                'gas': estimated_gas,
                'value': order_price,
            })
            signed_txn = w3.eth.account.sign_transaction(tx, decrypted_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            error_message = str(e)
            return jsonResponse(error_message, 400)
        return jsonResponse("", 200)
    except Exception as e:
        error_message = str(e)
        return jsonResponse(f"{str(e)} {contract.functions.status().call()}", 400)

if(__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port = 5002)