from flask import jsonify
from flask_restful import Resource, abort
from werkzeug.security import generate_password_hash

from . import db_session
from .tests import Tests
from .reqparse_test import parser


def abort_if_test_not_found(test_id):
    session = db_session.create_session()
    tests = session.query(Tests).get(test_id)
    if not tests:
        abort(404, message=f"Test {test_id} not found")


def set_password(password):
    return generate_password_hash(password)


class TestsResource(Resource):
    def get(self, test_id):
        abort_if_test_not_found(test_id)
        session = db_session.create_session()
        tests = session.query(Tests).get(test_id)
        return jsonify({'user': tests.to_dict(only=(
            'title', 'content', 'key', 'duration',
            'is_private', 'code', 'size', 'creator',))})

    def delete(self, test_id):
        abort_if_test_not_found(test_id)
        session = db_session.create_session()
        test = session.query(Tests).get(test_id)
        session.delete(test)
        session.commit()
        return jsonify({'success': 'OK'})


class TestsListResource(Resource):
    def get(self):
        session = db_session.create_session()
        tests = session.query(Tests).all()
        return jsonify({'tests': [item.to_dict(only=(
            'title', 'content', 'key', 'duration',
            'is_private', 'code', 'size', 'creator')) for item in tests]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        test = Tests(
            title=args['title'],
            content=args['content'],
            key=args['key'],
            duration=args['duration'],
            is_private=args['is_private'],
            code=args['code'],
            size=args['content'].count('{'),
            creator=args['creator']
        )
        session.add(test)
        session.commit()
        return jsonify({'success': 'OK'})
