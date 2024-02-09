from flask_sqlalchemy import SQLAlchemy


database = SQLAlchemy()


class ProductCategory(database.Model):
    __tablename__ = "productcategories"
    id = database.Column(database.Integer, primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), nullable=False)
    categoryId = database.Column(database.Integer, database.ForeignKey("categories.id"), nullable=False)

class ProductOrder(database.Model):
    __tablename__ = "productorders"
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), primary_key=True)
    orderId = database.Column(database.Integer, database.ForeignKey("orders.id"), primary_key=True)
    price = database.Column(database.Float, nullable=False)
    quantity = database.Column(database.Integer, nullable=False)

    product = database.relationship("Product", back_populates="productorders")
    order = database.relationship("Order", back_populates="orderItems")

class Product(database.Model):
    __tablename__ = "products"

    id = database.Column(database.Integer, primary_key = True)
    name = database.Column(database.String(256), nullable = False, unique = True)
    price = database.Column(database.Float, nullable = False)

    categories = database.relationship("Category", secondary= ProductCategory.__table__ , back_populates="products")
    orders = database.relationship("Order", secondary=ProductOrder.__table__, back_populates="products")
    productorders = database.relationship("ProductOrder", back_populates="product")



class Category(database.Model):
    __tablename__ = "categories"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary=ProductCategory.__table__, back_populates="categories")



class Order(database.Model):
    __tablename__ = "orders"

    id = database.Column(database.Integer, primary_key=True)
    timestamp = database.Column(database.DateTime, nullable= False)
    price = database.Column(database.Float, nullable= False)
    status =  database.Column(database.String(256), nullable= False)
    email = database.Column(database.String(256), nullable=False)
    address = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary= ProductOrder.__table__, back_populates="orders")
    orderItems = database.relationship("ProductOrder")
