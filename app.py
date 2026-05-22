from flask import Flask, render_template, request, send_file
from PIL import Image
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Steganography Logic ---
def message_to_bin(message):
    return ''.join(format(ord(i), '08b') for i in message)

def encode_logic(image_path, secret_message, output_path):
    img = Image.open(image_path)
    if img.mode != 'RGB': img = img.convert('RGB')
    encoded_img = img.copy()
    secret_message += "##"
    bin_secret_msg = message_to_bin(secret_message)
    data_len = len(bin_secret_msg)
    data_index = 0
    pixels = encoded_img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if data_index < data_len:
                r, g, b = pixels[x, y]
                if data_index < data_len: r = (r & ~1) | int(bin_secret_msg[data_index]); data_index += 1
                if data_index < data_len: g = (g & ~1) | int(bin_secret_msg[data_index]); data_index += 1
                if data_index < data_len: b = (b & ~1) | int(bin_secret_msg[data_index]); data_index += 1
                pixels[x, y] = (r, g, b)
            else: break
        if data_index >= data_len: break
    encoded_img.save(output_path)

# --- Web Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    file = request.files['image']
    msg = request.form['message']
    if file and msg:
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], "secret_" + file.filename)
        file.save(input_path)
        encode_logic(input_path, msg, output_path)
        return send_file(output_path, as_attachment=True)
    return "Error: File or Message missing"

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)