from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import logging
import config

transaction_app = Flask(__name__)

try:
    client = MongoClient(config.MONGO_URI)
    db = client.get_default_database()
    transactions_collection = db.transactions
    audit_collection = db.audit_logs
    logging.info("Transaction Service: Successfully connected to MongoDB.")
except Exception as e:
    logging.error(f"Transaction Service: Database connection error: {e}")
def get_user_id_from_header():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise ValueError("User ID not found in request headers.")
    return user_id

def log_transaction_audit(action, user_id, transaction_id=None, details=None):
    try:
        audit_collection.insert_one({
            'service': 'transaction', 'action': action, 'user_id': user_id,
            'transaction_id': transaction_id, 'details': details, 'timestamp': datetime.utcnow()
        })
    except Exception as e:
        logging.error(f"Transaction audit logging failed: {e}")

@transaction_app.route('/add', methods=['POST'])
def add_transaction():
    try:
        # Trust the header from the gateway to know which user this is.
        user_id = get_user_id_from_header()
        data = request.get_json()
        if not data or not all(k in data for k in ['amount', 'type', 'desc']):
            return jsonify({'error': 'amount, type, and desc fields required'}), 400

        transaction = {
            'user_id': user_id,
            'amount': float(data['amount']),
            'type': data['type'],
            'desc': data['desc'],
            'timestamp': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        result = transactions_collection.insert_one(transaction)
        transaction_id = str(result.inserted_id)
        log_transaction_audit('CREATE', user_id, transaction_id, transaction)
        return jsonify({'message': 'Transaction added successfully', 'transaction_id': transaction_id}), 201
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_app.route('/list', methods=['GET'])
def list_transactions():
    try:
        user_id = get_user_id_from_header()
        transactions = list(transactions_collection.find({'user_id': user_id}))
        for tx in transactions:
            tx['_id'] = str(tx['_id'])
            tx['timestamp'] = tx['timestamp'].isoformat()
            tx['created_at'] = tx['created_at'].isoformat()
        return jsonify({'transactions': transactions}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_app.route('/update/<tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    try:
        user_id = get_user_id_from_header()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Update data required'}), 400

        query = {'_id': ObjectId(tx_id), 'user_id': user_id}
        if not transactions_collection.find_one(query):
            return jsonify({'error': 'Transaction not found or unauthorized'}), 404

        update_fields = {}
        for field in ['amount', 'type', 'desc']:
            if field in data:
                update_fields[field] = data[field]

        if update_fields:
            update_fields['updated_at'] = datetime.utcnow()
            transactions_collection.update_one(query, {'$set': update_fields})
            log_transaction_audit('UPDATE', user_id, tx_id, update_fields)
            return jsonify({'message': 'Transaction updated successfully'}), 200
        else:
            return jsonify({'message': 'No fields to update'}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_app.route('/delete/<tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    try:
        user_id = get_user_id_from_header()
        query = {'_id': ObjectId(tx_id), 'user_id': user_id}
        result = transactions_collection.delete_one(query)

        if result.deleted_count == 0:
            return jsonify({'error': 'Transaction not found or unauthorized'}), 404

        log_transaction_audit('DELETE', user_id, tx_id)
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_app.route('/summary', methods=['GET'])
def transaction_summary():
    try:
        user_id = get_user_id_from_header()
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': '$type',
                'total_amount': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }}
        ]
        results = list(transactions_collection.aggregate(pipeline))
        summary = {res['_id']: {'total_amount': res['total_amount'], 'count': res['count']} for res in results}
        return jsonify({'summary': summary}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_app.route('/health')
def health():
    return jsonify({'status': 'Transaction Service running'})

if __name__ == '__main__':
    transaction_app.run(host='0.0.0.0', port=5002, debug=True)