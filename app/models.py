
# Example structure for MongoDB
def create_user(mongo, name, email, cv_path):
    mongo.db.users.insert_one({
        "name": name,
        "email": email,
        "cv_path": cv_path
    })
