from flask import Blueprint, jsonify, request, current_app
from app.models.user import LoginPayload
from pydantic import ValidationError
from app import db
from bson import ObjectId #responsavel por converter a string em id do mongo, na hr d buscar p conectar c o banco
from app.models.products import *
from app.models.sales import Sale 
from app.decorators import token_required
from datetime import datetime, timedelta, timezone
import jwt
import csv
import os
import io

main_bp = Blueprint('main_bp', __name__)
# ********** REQUISITOS FUNCIONAIS **********

# RF: o sistema deve permitir que o calouro se autentique para obter um token
@main_bp.route('/login', methods=['POST'])
def login():
    try:
        raw_data = request.get_json()
        user_data = LoginPayload(**raw_data)

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": "Erro durante a requisição do dado"}), 500
    if user_data.username == "calouro" and user_data.password == 'eng123':
        token = jwt.encode(
            {
                "user_id": user_data.username,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30)

            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return jsonify({'acess_token': token}), 200
    
    return jsonify({"error": "Credenciais inválidas"}), 401
                        


# RF: o sistema deve permitir listagem dos produtos
@main_bp.route('/products', methods=['GET'])
def get_products():
    products_cursor = db.products.find({})
    products_list = [ProductDBModel(**product).model_dump(by_alias=True, exclude_none=True) for product in products_cursor]
    return jsonify(products_list)

# RF: o sistema deve permitir a criação de um novo produto
@token_required
@main_bp.route('/products', methods=['POST'])
def create_product(token):
    try:
        product = Product(**request.get_json())
    
    except ValidationError as e:
        return jsonify({"error": e.errors()})
    
    result = db.products.insert_one(product.model_dump())
    return jsonify({"message": "Produto criado com sucesso",
                     "product_id": str(result.inserted_id)}), 201


# RF o sistema deve permitir a visualização dos detalhes de um produto específico
@main_bp.route('/products/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    try:
        oid = ObjectId(product_id)
    
    except Exception as e:
        return jsonify({"error": f"Erro ao transformar o {product_id} em ObjectId: {e}"})
    
    product = db.products.find_one({'_id': oid})
    if product:
        product_model = ProductDBModel(**product),model_dump(by_alias=True, exclude_none=True)

        return jsonify(products_list)
    else:
        return jsonify({"message": f"Produto com ID {product_id} não encontrado"})


# RF: o sistema deve permitir a atualização de um unico produto e produto existente
@main_bp.route('/products/<string:product_id>', methods=['PUT'])
@token_required
def update_product(token, product_id):
    try:
        oid = ObjectId(product_id)
        update_data = UpdateProduct(**request.get_json())

    except ValidationError as e:
        return jsonify({"error": e.errors()})
    
    update_result = db.products.update_one(
        {"_id": oid},
        {"$set": update_data.model_dump(exclude_unset=True)}
        
    )
    if update_result.matched_count ==0:
        return jsonify({"message": "Produto não encontrado"}), 404
 
    updated_product = db.products.find_one({"_id": oid})
    return jsonify(ProductDBModel(**updated_product).model_dump(by_alias=True, exclude_none=True))


# RF: o sistema deve permitir a deleção de um unico produto e produto existente
@main_bp.route('/products/<string:product_id>', methods=['DELETE'])
@token_required
def delete_product(token, product_id):
    try:
        oid = ObjectId(product_id)
    except Exception:
        return jsonify({"error": "ID inválido"})
    
    delete_product = db.products.delete_one({'_id': oid})
    if delete_product.deleted_count ==0:
        return jsonify({"message": f"Produto não encontrado"}), 404
    
    return "", 204


# RF: o sistema deve permitir a importação de vendas através de um arquivo
@main_bp.route('/sales/upload', methods=['POST'])
@token_required
def upload_sales(token):
    if not 'file' in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and file.filename.endswith('.csv'):
        csv_stream = io.StringIO(file.stream.read().decode('UTF-8'),newline=None)
        csv_reader = csv.DictReader(csv_stream)
        
        sales_to_insert = []
        error = []

        for row_num, row in enumerate(csv_reader, 1):
            try:
                sale_data = Sale(**row)

                sales_to_insert.append(sale_data.model_dump())

            except ValidationError as e:
                error.append(f'Linha {row_num} com dados inválidos')
            except Exception:
                error.append(f'Linha {row_num} com erro desconhecido')
            
        if sales_to_insert:
            try:
                db.sales.insert_many(sales_to_insert)
            except Exception as e:
                return jsonify({'error': f'{e}'})
        return jsonify({
            "message": "Upload concluído",
            "sales_imported": len(sales_to_insert),
            "erros": error
        }), 200
                            

    
    return jsonify({"message": "Importar vendas através de um arquivo"})

#ROTA RAIZ
@main_bp.route('/')
def index():
    return jsonify({"message": "Seja bem vindo(a) na faculdade de Engenharia!"})




