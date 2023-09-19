import os
import json

from flask import Flask
from configuration import Configuration
from flask_migrate import Migrate, init, migrate, upgrade
from models import database, Role, User
from sqlalchemy_utils import database_exists, create_database

from web3 import Web3, HTTPProvider, Account

w3 = Web3(HTTPProvider('http://ganache:8545'))

application = Flask(__name__)
application.config.from_object(Configuration)

migrateObject = Migrate(application, database)

if not database_exists(application.config["SQLALCHEMY_DATABASE_URI"]):
    create_database(application.config["SQLALCHEMY_DATABASE_URI"])

database.init_app(application)

with application.app_context() as context:
    init()
    migrate(message="Production migration")
    upgrade()

    ownerRole = Role(name="owner")
    customerRole = Role(name="customer")
    courierRole = Role(name="courier")

    database.session.add(ownerRole)
    database.session.add(customerRole)
    database.session.add(courierRole)
    database.session.commit()

    owner = User(
        email = "onlymoney@gmail.com",
        password = "evenmoremoney",
        forename = "Scrooge",
        surname = "McDuck",
        roleId = ownerRole.id
    )
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider('http://host.docker.internal:8545'))


    private_key = "0xb64be88dd6b89facf295f4fd0dda082efcbe95a2bb4478f5ee582b7efe88cf60"
    account = w3.eth.account.from_key(private_key)
    owner_address = account.address
    owner.key = owner_address
    balance_wei = w3.eth.get_balance(w3.eth.accounts[0]) // 2
    encrypted_key = Account.encrypt(private_key, "iep-project")
    with open("/data/keyfile.json", "w") as keyfile:
        json.dump(encrypted_key, keyfile)

    gas_price = w3.eth.gas_price
    gas_estimate = w3.eth.estimate_gas({
        'from': w3.eth.accounts[0],
        'to': owner_address,
        'value': balance_wei,
    })

    # Calculate the gas cost in wei
    total_gas_cost = gas_price * gas_estimate

    # Calculate the maximum amount you can send after covering gas costs
    sendable_amount = balance_wei - total_gas_cost
    # Send the transaction
    txn_hash = w3.eth.send_transaction({
        'from': w3.eth.accounts[0],
        'to': owner_address,
        'value': sendable_amount,
        'gas': gas_estimate,
        'gasPrice': gas_price
    })

    database.session.add(owner)
    database.session.commit()

