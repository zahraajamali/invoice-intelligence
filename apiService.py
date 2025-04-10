from flask import Flask, jsonify
import requests


def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# app = Flask(__name__)

# @app.route('/')
# def get_data():
#     try:
#         response1 = requests.get('https://api.example.com/data1')
#         response2 = requests.get('https://api.example.com/data2')

#         response1.raise_for_status()
#         response2.raise_for_status()

#         data1 = response1.json()
#         data2 = response2.json()

#         return jsonify({
#             'data1': data1,
#             'data2': data2
#         })

#     except requests.exceptions.RequestException as e:
#         return jsonify({'error': str(e)}), 500


# if __name__ == '__main__':
#     app.run(debug=True)