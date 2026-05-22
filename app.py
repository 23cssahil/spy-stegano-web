from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
import os
import werkzeug

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Limit file size to 16MB

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Robust Steganography Logic ---

def message_to_bin(message_str):
    # Convert string to bytes with UTF-8 to support all special characters, Hindi, and emojis
    # We append a unique high-security sentinel to easily detect the end of the message
    encoded_bytes = (message_str + "$$SPY_STEGANO$$").encode('utf-8')
    return ''.join(format(b, '08b') for b in encoded_bytes)

def encode_logic(image_path, secret_message, output_path):
    img = Image.open(image_path)
    
    # We convert image to RGB or RGBA. 
    # If the image has transparency (RGBA), we preserve the alpha channel 
    # and only hide data in the RGB channels.
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
        
    encoded_img = img.copy()
    bin_secret_msg = message_to_bin(secret_message)
    data_len = len(bin_secret_msg)
    
    width, height = img.size
    # We only hide in R, G, B channels to avoid corrupting transparency
    max_capacity = width * height * 3
    
    if data_len > max_capacity:
        raise ValueError(f"Message is too long for this image! Maximum characters allowed: {(max_capacity // 8) - 15}")
        
    data_index = 0
    pixels = encoded_img.load()
    
    for y in range(height):
        for x in range(width):
            if data_index >= data_len:
                break
                
            pixel = list(pixels[x, y]) # list representation of (r, g, b) or (r, g, b, a)
            for c in range(3): # Only edit first 3 channels (R, G, B)
                if data_index < data_len:
                    pixel[c] = (pixel[c] & ~1) | int(bin_secret_msg[data_index])
                    data_index += 1
            
            pixels[x, y] = tuple(pixel)
            
        if data_index >= data_len:
            break
            
    # CRITICAL: We MUST save as PNG (lossless) to preserve LSB bits.
    # Saving as JPEG would destroy the hidden message due to lossy compression.
    encoded_img.save(output_path, format="PNG")

def decode_logic(image_path):
    img = Image.open(image_path)
    
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
        
    pixels = img.load()
    width, height = img.size
    
    binary_bits = []
    
    # Read LSB bits from the R, G, B channels of each pixel
    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            for c in range(3): # Read R, G, B channels
                binary_bits.append(str(pixel[c] & 1))
                
    # Group bits into bytes (8 bits each)
    byte_list = []
    for i in range(0, len(binary_bits), 8):
        byte_bits = binary_bits[i:i+8]
        if len(byte_bits) < 8:
            break
        byte_val = int(''.join(byte_bits), 2)
        byte_list.append(byte_val)
        
    all_bytes = bytearray(byte_list)
    
    # Look for the UTF-8 encoded sentinel in the byte array
    sentinel = "$$SPY_STEGANO$$".encode('utf-8')
    sentinel_idx = all_bytes.find(sentinel)
    
    if sentinel_idx != -1:
        # Decode only the message before the sentinel
        decoded_bytes = all_bytes[:sentinel_idx]
        try:
            return decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return "Error: Could not decode UTF-8 message. The message might be corrupted."
    else:
        return "No secret message found in this image! It might be a regular image or corrupted."

# --- Web Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encode', methods=['POST'])
def encode():
    try:
        if 'image' not in request.files or 'message' not in request.form:
            return jsonify({"status": "error", "message": "Missing image file or secret message!"}), 400
            
        file = request.files['image']
        message = request.form['message']
        
        if file.filename == '' or not message:
            return jsonify({"status": "error", "message": "Invalid file or empty secret message!"}), 400
            
        # Secure the filename and change extension to png
        filename = werkzeug.utils.secure_filename(file.filename)
        name_part, _ = os.path.splitext(filename)
        output_filename = f"secret_{name_part}.png"
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Save temp input
        file.save(input_path)
        
        # Encode
        try:
            encode_logic(input_path, message, output_path)
        except ValueError as val_err:
            # Clean up temp file
            if os.path.exists(input_path):
                os.remove(input_path)
            return jsonify({"status": "error", "message": str(val_err)}), 400
            
        # Clean up temp file
        if os.path.exists(input_path):
            os.remove(input_path)
            
        return jsonify({
            "status": "success",
            "message": "Message successfully hidden inside image!",
            "download_url": f"/download/{output_filename}",
            "filename": output_filename
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

@app.route('/decode', methods=['POST'])
def decode():
    try:
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "No image uploaded for decoding!"}), 400
            
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "Invalid file!"}), 400
            
        filename = werkzeug.utils.secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"decode_{filename}")
        
        file.save(temp_path)
        
        # Decode
        extracted_message = decode_logic(temp_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if extracted_message.startswith("No secret message found") or extracted_message.startswith("Error:"):
            return jsonify({
                "status": "error",
                "message": extracted_message
            })
            
        return jsonify({
            "status": "success",
            "message": "Secret message extracted successfully!",
            "secret_message": extracted_message
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

@app.route('/download/<filename>')
def download(filename):
    # Prevent directory traversal attacks
    filename = os.path.basename(filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)