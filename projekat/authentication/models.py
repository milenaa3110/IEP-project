from flask_sqlalchemy import SQLAlchemy


database = SQLAlchemy()

class User(database.Model):
    __tablename__ = "users"

    id = database.Column(database.Integer, primary_key = True)
    email = database.Column(database.String(256), nullable = False, unique = True)
    password = database.Column(database.String(256), nullable = False)
    forename = database.Column(database.String(256), nullable = False)
    surname = database.Column(database.String(256), nullable = False)
    key = database.Column(database.String(256), nullable=True)

    roleId = database.Column(database.Integer, database.ForeignKey("roles.id"), nullable = False)
    role = database.relationship("Role", back_populates="users")

class Role(database.Model):
    __tablename__ = "roles"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)

    users = database.relationship("User", back_populates="role")