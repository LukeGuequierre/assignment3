from flask import Flask, redirect, request, url_for
from flask import Response

import requests

from flask import request
from flask import Flask, render_template

from jinja2 import Template
import secrets

import base64
import json
import os


from flask import session


app = Flask(__name__)

app.secret_key = secrets.token_hex()


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, ForeignKey, String

from logging.config import dictConfig


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    },
     'file.handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'weatherportal.log',
            'maxBytes': 10000000,
            'backupCount': 5,
            'level': 'DEBUG',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file.handler']
    }
})

# Not required for assignment3
in_mem_cities = []
in_mem_user_cities = {}


# SQLite Database creation
Base = declarative_base()
engine = create_engine("sqlite:///weatherportal.db", echo=True, future=True)
DBSession = sessionmaker(bind=engine)


@app.before_first_request
def create_tables():
    Base.metadata.create_all(engine)


class Admin(Base):
    __tablename__ = 'admin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<Admin(name='%s')>" % (self.name)

    # Ref: https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<User(name='%s')>" % (self.name)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class AdminCity(Base):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey('admin.id'))
    name = Column(String)
    url = Column(String)

    def __repr__(self):
        return "<AdminCity(name='%s')>" % (self.name)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class UserCity(Base):
    __tablename__ = 'user_cities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cityId = Column(Integer, ForeignKey('cities.id'))
    userId = Column(Integer, ForeignKey('users.id'))
    month = Column(String)
    year = Column(String)
    weather_params = Column(String)

    def __repr__(self):
        return "<UserCity(userId='%s', cityId='%s')>" % (self.userId, self.cityId)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


## Admin REST API
@app.route("/admin", methods=['POST'])
def add_admin():
    app.logger.info("Inside add_admin")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    name = data['name']
    password = data['password']

    admin = Admin(name=name, password=password)

    am_session = DBSession()
    am_session.add(admin)
    am_session.commit()

    return admin.as_dict()


@app.route("/admin/<id>")
def get_admin_by_id(id):
    app.logger.info("Inside get_admin_by_id %s\n", id)

    am_session = DBSession()
    admin = am_session.get(Admin, id)

    app.logger.info("Found admin:%s\n", str(admin))
    if admin is None:
        status = ("Admin with id {id} not found\n").format(id=id)
        return Response(status, status=404)
    else:
        return admin.as_dict()


@app.route("/admin/<id>", methods=['DELETE'])
def delete_admin_by_id(id):
    app.logger.info("Inside delete_admin_by_id %s\n", id)

    am_session = DBSession()
    admin = am_session.query(Admin).filter_by(id=id).first()

    app.logger.info("Found admin:%s\n", str(admin))
    if admin is None:
        status = ("Admin with id {id} not found.\n").format(id=id)
        return Response(status, status=404)
    else:
        am_session.delete(admin)
        am_session.commit()
        status = ("Admin with id {id} deleted.\n").format(id=id)
        return Response(status, status=200)

@app.route("/admins")
def get_admins():
    app.logger.info("Inside get_admins")
    ret_obj = {}

    am_session = DBSession()
    admins = am_session.query(Admin)
    admin_list = []
    for admin in admins:
        admin_list.append(admin.as_dict())

    ret_obj['admins'] = admin_list
    return ret_obj


##User REST API
@app.route("/users", methods=['POST'])
def add_users():
    app.logger.info("Inside add_users")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    name = data['name']
    password = data['password']

    us_session = DBSession()

    existing = us_session.query(User).filter_by(name=name).first()
    if existing:
        return Response("User with {} already exists.".format(name), status=400)

    user = User(name=name, password=password)
    us_session.add(user)
    us_session.commit()

    return user.as_dict()


@app.route("/users")
def get_users():
    app.logger.info("Inside get_users")
    ret_obj = {}

    us_session = DBSession()
    users = us_session.query(User)
    user_list = []
    for user in users:
        user_list.append(user.as_dict())

    ret_obj['users'] = user_list
    return ret_obj


@app.route("/users/<id>")
def get_user_by_id(id):
    app.logger.info("Inside get_users_by_id %s\n", id)

    us_session = DBSession()
    user = us_session.get(User, id)

    app.logger.info("Found user:%s\n", str(user))
    if user is None:
        status = ("User with id {id} not found\n").format(id=id)
        return Response(status, status=404)
    else:
        return user.as_dict()


@app.route("/users/<id>", methods=['DELETE'])
def delete_user_by_id(id):
    app.logger.info("Inside delete_users_by_id %s\n", id)

    us_session = DBSession()
    user = us_session.query(User).filter_by(id=id).first()

    app.logger.info("Found user:%s\n", str(user))
    if user is None:
        status = ("User with id {id} not found.\n").format(id=id)
        return Response(status, status=404)
    else:
        us_session.delete(user)
        us_session.commit()
        status = ("User with id {id} deleted.\n").format(id=id)
        return Response(status, status=200)


## Admin Cities REST API
@app.route("/admin/<id>/cities", methods=['POST'])
def add_city_admin(id):
    app.logger.info("Inside add_city_admin")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    cs_session = DBSession()

    admin = cs_session.get(Admin, id)
    if admin is None:
        return Response("Admin with id {} not found".format(id), status=404)

    name = data['name']
    url = data['url']

    city = AdminCity(admin_id=id, name=name, url=url)
    cs_session.add(city)
    cs_session.commit()

    return city.as_dict()


@app.route("/admin/<id>/cities")
def get_cities_admin(id):
    app.logger.info("Inside get_cities_admin")

    cs_session = DBSession()

    admin = cs_session.get(Admin, id)
    if admin is None:
        return Response("Admin with id {} not found".format(id), status=404)

    cities = cs_session.query(AdminCity).filter_by(admin_id=id)
    city_list = []
    for city in cities:
        city_list.append(city.as_dict())

    return {'cities': city_list}


@app.route("/admin/<id>/cities/<city_id>")
def get_city_by_id_admin(id, city_id):
    app.logger.info("Inside get_city_by_id_admin, admin:%s city:%s\n", id, city_id)

    cs_session = DBSession()

    admin = cs_session.get(Admin, id)
    if admin is None:
        return Response("Admin with id {} not found".format(id), status=404)

    city = cs_session.get(AdminCity, city_id)
    if city is None:
        return Response("City with id {} not found".format(city_id), status=404)

    return city.as_dict()


@app.route("/admin/<id>/cities/<city_id>", methods=['DELETE'])
def delete_city_by_id(id, city_id):
    app.logger.info("Inside delete_city_by_id, admin:%s city:%s\n", id, city_id)

    cs_session = DBSession()

    admin = cs_session.get(Admin, id)
    if admin is None:
        return Response("Admin with id {} not found".format(id), status=404)

    city = cs_session.query(AdminCity).filter_by(id=city_id).first()
    if city is None:
        return Response("City with id {} not found".format(city_id), status=404)
    else:
        cs_session.delete(city)
        cs_session.commit()
        return Response("City with id {} deleted.".format(city_id), status=200)


## User Cities REST API
@app.route("/users/<id>/cities", methods=['POST'])
def add_city_user(id):
    app.logger.info("Inside add_city_user")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    cs_session = DBSession()

    user = cs_session.get(User, id)
    if user is None:
        return Response("User with id {} not found".format(id), status=404)

    city_name = data['name']
    month = data['month']
    year = data['year']
    weather_params = data['weather_params']
    
    if not str(year).isdigit() or len(str(year)) != 4:
        return Response("Year needs to be exactly four digits.", status=400)
    city = cs_session.query(AdminCity).filter_by(name=city_name).first()
    if city is None:
        return Response("City with name {} not found".format(city_name), status=404)

    user_city = UserCity(cityId=city.id, userId=id, month=month, year=year, weather_params=weather_params)
    cs_session.add(user_city)
    cs_session.commit()

    return user_city.as_dict()

@app.route("/user/<id>/cities")
def get_cities_user(id):
    app.logger.info("Inside get_cities_user")

    cs_session = DBSession()

    user = cs_session.get(User, id)
    if user is None:
        return Response("User with id {} not found".format(id), status=404)

    cities = cs_session.query(UserCity).filter_by(user_id=id)
    city_list = []
    for city in cities:
        city_list.append(city.as_dict())

    return {'cities': city_list}

    
@app.route("/users/<id>/cities/<city_id>")
def get_city_by_id_user(city_id):
    app.logger.info("Inside get_city_by_id_user %s\n", city_id)

    cs_session = DBSession()
    city = cs_session.get(UserCity, city_id)
    user = cs_session.get(User, id)
    app.logger.info("Found city:%s\n", str(city))
    if city == None:
        status = ("City with id {city_id} not found\n").format(id=city_id)
        return Response(status, status=404)
    if user == None:
        status = ("User with id {id} not found\n").format(id=id)
        return Response(status, status=404)
    else:
        return city.as_dict()
        
@app.route("/logout",methods=['GET'])
def logout():
    app.logger.info("Logout called.")
    session.pop('username', None)
    app.logger.info("Before returning...")
    return render_template('index.html')


@app.route("/login", methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    my_cities = []
    if username in in_mem_user_cities:
        my_cities = in_mem_user_cities[username]
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal",
            cities=my_cities,
            name=username,
            addButton_style="display:none;",
            addCityForm_style="display:none;",
            regButton_style="display:inline;",
            regForm_style="display:inline;",
            status_style="display:none;")


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/adminlogin", methods=['POST'])
def adminlogin():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    user_cities = in_mem_cities
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal - Admin Panel",
            cities=user_cities,
            name=username,
            addButton_style="display:inline;",
            addCityForm_style="display:inline;",
            regButton_style="display:none;",
            regForm_style="display:none;",
            status_style="display:none;")


@app.route("/admin")
def adminindex():
    return render_template('adminindex.html')


if __name__ == "__main__":

    app.debug = False
    app.logger.info('Portal started...')
    app.run(host='0.0.0.0', port=5009) 
