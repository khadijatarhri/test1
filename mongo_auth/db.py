from django.conf import settings
import urllib.parse
from pymongo import MongoClient

db_host = settings.MANGO_JWT_SETTINGS["db_host"]
db_port = settings.MANGO_JWT_SETTINGS["db_port"]
db_name = settings.MANGO_JWT_SETTINGS["db_name"]
db_user = settings.MANGO_JWT_SETTINGS.get("db_user")
db_pass = settings.MANGO_JWT_SETTINGS.get("db_pass")

# Construction de l'URI MongoDB
if db_user and db_pass:
    user = urllib.parse.quote(db_user)
    password = urllib.parse.quote(db_pass)
    mongo_uri = f"mongodb://{user}:{password}@{db_host}:{db_port}/{db_name}"
else:
    mongo_uri = f"mongodb://{db_host}:{db_port}/{db_name}"

client = MongoClient(mongo_uri)
db = client[db_name]
auth_collection = db["users"]
jwt_secret = db["jwt_secrets"]
jwt_life = 3600
fields = ["email", "password"]
secondary_username_field = "username"

database = db
