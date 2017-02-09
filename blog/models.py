from passlib.hash import bcrypt
from datetime import datetime
from helpers import get_session, create_user
import os
import uuid
from neo4j.v1 import GraphDatabase, basic_auth


class User:
    def __init__(self, username):
        self.username = username

    def find(self):
        session = get_session()
        result = session.run("MATCH (u:User {username: {username}}) RETURN u.username AS username, u.password AS password", {"username": self.username})
        results = list(result)
        session.close()
        #should come back to this
        if len(results) >0:
            return (results[0])
        return False

    def register(self, password):
        if not self.find():
            create_user(username=self.username, password=bcrypt.encrypt(password))
            return True
        else:
            return False

    def verify_password(self, password):
        user = self.find()
        print(user)
        if user:
            return bcrypt.verify(password, user['password'])
        else:
            return False

    

def timestamp():
    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    delta = now - epoch
    return delta.total_seconds()

def date():
    return datetime.now().strftime('%Y-%m-%d')
