from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps
    def decorated(*args, **kwargs):
        
        token = None
        if  'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            

            except IndexError:
                return jsonify({'message': 'Token inválido'})
        
        if not token:
            return jsonify({'error': 'Token não encontrado'}), 401
        
        try:
            data = jwt.decode(token,
                               current_app.config['SECRET_KEY'], algorithms=['HS256'])

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(data, *args, **kwargs)
       
    return decorated