import datetime
import json
import re
import io
import csv
import os
import ast
import subprocess
from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, Product, ProductOrder, ProductCategory, Order, Category
from email.utils import parseaddr
from sqlalchemy import func
from sqlalchemy.orm import session
from sqlalchemy import and_
from roleCheckDecorator  import roleCheck
from flask_jwt_extended import JWTManager, jwt_required
from pyspark.sql import SparkSession, functions as F

def jsonResponse(message, status):
    responseData = {}
    responseData["message"] = message
    return Response(json.dumps(responseData), status = status)

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

@application.route("/update", methods=["POST"])
@jwt_required()
@roleCheck("owner")
def update():

    # check if file is sent
    if "file" not in request.files.keys():
        return jsonResponse("Field file is missing.", 400)

    fileContent = request.files["file"].stream.read().decode("utf-8")
    stream = io.StringIO(fileContent)
    reader = csv.reader(stream)

    products = []

    for index, row in enumerate(reader):
        if len(row) != 3:
            return jsonResponse("Incorrect number of values on line " + str(index) + ".", 400)
        categories = row[0].split("|")
        if len(categories) == 0:
            return  jsonResponse("Incorrect number of values on line " + str(index) + ".", 400)
        for category in categories:
            if len(category) == 0:
                return jsonResponse("Incorrect number of values on line " + str(index) + ".", 400)
        name = row[1]
        if len(name) == 0:
            return jsonResponse("Incorrect number of values on line " + str(index) + ".", 400)
        price = row[2]
        if len(price) == 0:
            return jsonResponse("Incorrect quantity on line " + str(index) + ".", 400)
        else:
            try:
                price = float(price)
                if price <= 0:
                    return jsonResponse("Incorrect price on line " + str(index) + ".", 400)
            except ValueError:
                return jsonResponse("Incorrect price on line " + str(index) + ".", 400)
        query = Product.query.filter(Product.name == name)

        if query.first() is not None:
            return jsonResponse("Product {} already exists.".format(name), 400)

        newProduct = {
            "categories": categories,
            "name": name,
            "price": price
        }

        products.append(newProduct)
    for product in products:

        newProduct = Product.query.filter(Product.name == product["name"]).first()

        # creating product if it doesnt exist
        if newProduct is None:
            newProduct = Product(name=product["name"],
                              price=float(product["price"]))
            database.session.add(newProduct)
            database.session.commit()

            # fetching categories from JSON
            categories = product["categories"]

            for cat in categories:

                category = Category.query.filter(Category.name == cat).first()

                # if category doesnt exist in db, insert it and link it to product
                if (category is None):
                    category = Category(name=cat)
                    database.session.add(category)
                    database.session.commit()
                    link = ProductCategory(productId=newProduct.id, categoryId=category.id)
                    database.session.add(link)
                    database.session.commit()
                else:
                    link = ProductCategory(productId=newProduct.id, categoryId=category.id)
                    database.session.add(link)
                    database.session.commit()
        else:
            flag = True
            categories = redisObj["categories"]
            if len(categories) != len(newProduct.categories):
                flag = False
            for category in categories:
                if category not in [cat.name for cat in newProduct.categories]:
                    flag = False
                    print("Rejected " + newProduct.name)
                    print(json.dumps([cat.name for cat in newProduct.categories]))
                    print(json.dumps(redisObj))
                    break
    return Response("", status= 200)


def parseResult(result):
    match = re.search(r"result=(.*?)\n", result)

    if match:
        extracted_result = match.group(1).strip()  # Group 1 captures the content inside the parenthesis
        return extracted_result
    return "error"


@application.route("/product_statistics", methods=["GET"])
@roleCheck("owner")
def productStatistics():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/opt/src/owner/productStatistics.py"
    os.environ["SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"
    result = subprocess.check_output(["/template.sh"])
    try:
        result = parseResult(result.decode())
        result = json.loads(result)
        return jsonify(result)
    except Exception as e:
        return jsonResponse(f"{result} {str(e)}", 400)

    '''
    resultObj = {}
    resultObj["statistics"] = []

    products = Product.query.all()

    for product in products:
        statObj = {}
        statObj["name"] = product.name
        statObj["sold"] = 0
        statObj["waiting"] = 0

        for item in product.productorders:
            statObj["sold"] += item.quantityOrdered
            statObj["waiting"] += item.quantityOrdered - item.quantityRecieved

        if statObj["sold"] > 0:
            resultObj["statistics"].append(statObj)

    return resultObj
'''

@application.route("/category_statistics", methods=["GET"])
@roleCheck("owner")
def categoryStatistics():
    os.environ["SPARK_APPLICATION_PYTHON_LOCATION"] = "/opt/src/owner/categoryStatistics.py"
    os.environ[
        "SPARK_SUBMIT_ARGS"] = "--driver-class-path /app/mysql-connector-j-8.0.33.jar --jars /app/mysql-connector-j-8.0.33.jar"
    result = subprocess.check_output(["/template.sh"])
    try:
        result = parseResult(result.decode())
        result = json.loads(result)
        return jsonify(result)
    except Exception as e:
        return jsonResponse(f"{result} {str(e)}", 400)

    '''
    resultObj = {}
    resultObj["statistics"] = []

    catDict = {cat.id :
               {
                "category": cat,
                "productsSold": 0
    } for cat in Category.query.all()}


    for product in Product.query.all():
        sold = 0
        for item in product.productorders:
            sold += item.quantityOrdered

        for cat in product.categories:
            catDict[cat.id]["productsSold"] += sold

    catList = list(catDict.values())
    # treba da bude desc po productsSold, a asc po category.name

    catList = sorted(sorted(catList, key = lambda x:  x["category"].name), key = lambda x: x["productsSold"], reverse=True)
    resultObj["statistics"] = [cat["category"].name for cat in catList]


    return resultObj
    '''

if(__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port = 5001)