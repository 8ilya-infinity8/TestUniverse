from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('content', required=True)
parser.add_argument('key', required=True)
parser.add_argument('duration', required=True, type=int)
parser.add_argument('is_private', required=True, type=bool)
parser.add_argument('code', required=True)
parser.add_argument('creator', required=True, type=int)
