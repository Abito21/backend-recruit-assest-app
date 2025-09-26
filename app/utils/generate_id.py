import bson


def generate_id():
    return str(bson.ObjectId())
