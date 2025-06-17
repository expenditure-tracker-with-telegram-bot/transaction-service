# transaction_service/app.py
from flask import Flask, request, jsonify
from bson import ObjectId
from datetime import datetime, timedelta
from config import db, PORT

app = Flask(__name__)

transactions_collection = db.transactions

def get_user_from_headers():
    return request.headers.get('X-User', '')

def get_role_from_headers():
    return request.headers.get('X-Role', '')

@app.route('/health')
def health():
    return jsonify({'status': 'Transaction Service running', 'port': PORT})

@app.route('/add', methods=['POST'])
def add_transaction():
    try:
        user = get_user_from_headers()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        amount = data.get('amount')
        tx_type = data.get('type')
        desc = data.get('desc')

        if not amount or not tx_type:
            return jsonify({'error': 'Amount and type are required'}), 400

        transaction = {
            'user': user,
            'amount': float(amount),
            'type': tx_type,
            'desc': desc or '',
            'timestamp': datetime.utcnow()
        }

        result = transactions_collection.insert_one(transaction)

        return jsonify({
            'message': 'Transaction created',
            'id': str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/list', methods=['GET'])
def list_transactions():
    try:
        user = get_user_from_headers()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401

        transactions = list(transactions_collection.find({'user': user}))

        # Convert ObjectId to string
        for tx in transactions:
            tx['_id'] = str(tx['_id'])
            tx['timestamp'] = tx['timestamp'].isoformat()

        return jsonify({'transactions': transactions}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update/<tx_id>', methods=['PUT'])
def update_transaction(tx_id):
    try:
        user = get_user_from_headers()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401

        # Check if transaction exists and belongs to user
        transaction = transactions_collection.find_one({
            '_id': ObjectId(tx_id),
            'user': user
        })

        if not transaction:
            return jsonify({'error': 'Transaction not found or unauthorized'}), 404

        data = request.get_json()
        update_data = {}

        if 'amount' in data:
            update_data['amount'] = float(data['amount'])
        if 'type' in data:
            update_data['type'] = data['type']
        if 'desc' in data:
            update_data['desc'] = data['desc']

        update_data['updated_at'] = datetime.utcnow()

        transactions_collection.update_one(
            {'_id': ObjectId(tx_id)},
            {'$set': update_data}
        )

        return jsonify({'message': 'Transaction updated'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    try:
        user = get_user_from_headers()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401

        result = transactions_collection.delete_one({
            '_id': ObjectId(tx_id),
            'user': user
        })

        if result.deleted_count == 0:
            return jsonify({'error': 'Transaction not found or unauthorized'}), 404

        return jsonify({'message': 'Transaction deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    try:
        user = get_user_from_headers()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401

        pipeline = [
            {'$match': {'user': user}},
            {
                '$group': {
                    '_id': '$type',
                    'total': {'$sum': '$amount'},
                    'count': {'$sum': 1}
                }
            }
        ]

        summary = list(transactions_collection.aggregate(pipeline))

        return jsonify({'summary': summary}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin endpoints
@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    try:
        role = get_role_from_headers()
        if role != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        total_transactions = transactions_collection.count_documents({})

        # Transactions per day (last 7 days)
        pipeline = [
            {
                '$match': {
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=7)
                    }
                }
            },
            {
                '$group': {
                    '_id': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',
                            'date': '$timestamp'
                        }
                    },
                    'count': {'$sum': 1}
                }
            }
        ]

        daily_stats = list(transactions_collection.aggregate(pipeline))

        return jsonify({
            'total_transactions': total_transactions,
            'daily_stats': daily_stats
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)