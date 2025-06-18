import os
from functools import wraps
from flask import Flask, request, jsonify, g
from bson import ObjectId
from datetime import datetime
from config import db, PORT

app = Flask(__name__)

transactions_collection = db.transactions

def get_user_from_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = request.headers.get('X-User-Username')
        role = request.headers.get('X-User-Role')
        if not username:
            return jsonify({'error': 'User identity not found in request headers'}), 401
        g.user = username
        g.role = role
        return f(*args, **kwargs)
    return decorated_function

@app.route('/add', methods=['POST'])
@get_user_from_headers
def add_transaction():
    data = request.get_json() or {}
    if not data.get('amount') or not data.get('type'):
        return jsonify({'error': 'Amount and type required'}), 400

    txn = {
        'user': g.user,
        'amount': float(data.get('amount')),
        'type': data.get('type'),
        'desc': data.get('desc', ''),
        'timestamp': datetime.utcnow()
    }
    res = transactions_collection.insert_one(txn)
    return jsonify({'message': 'Created', 'id': str(res.inserted_id)}), 201

@app.route('/list', methods=['GET'])
@get_user_from_headers
def list_transactions():
    docs = list(transactions_collection.find({'user': g.user}))
    for d in docs:
        d['_id'] = str(d['_id'])
        d['timestamp'] = d['timestamp'].isoformat()
    return jsonify({'transactions': docs}), 200

@app.route('/update/<tx_id>', methods=['PUT'])
@get_user_from_headers
def update_transaction(tx_id):
    doc = transactions_collection.find_one({'_id': ObjectId(tx_id), 'user': g.user})
    if not doc:
        return jsonify({'error': 'Not found or unauthorized'}), 404

    data = request.get_json() or {}
    update_data = {key: data[key] for key in ['amount', 'type', 'desc'] if key in data}
    update_data['updated_at'] = datetime.utcnow()

    transactions_collection.update_one({'_id': ObjectId(tx_id)}, {'$set': update_data})
    return jsonify({'message': 'Updated'}), 200

@app.route('/delete/<tx_id>', methods=['DELETE'])
@get_user_from_headers
def delete_transaction(tx_id):
    res = transactions_collection.delete_one({'_id': ObjectId(tx_id), 'user': g.user})
    if res.deleted_count == 0:
        return jsonify({'error': 'Not found or unauthorized'}), 404
    return jsonify({'message': 'Deleted'}), 200

@app.route('/admin/stats', methods=['GET'])
@get_user_from_headers
def admin_stats():
    if g.role != 'Admin':
        return jsonify({'error': 'Admin access required'}), 403

    total = transactions_collection.count_documents({})
    return jsonify({'total_transactions': total}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)