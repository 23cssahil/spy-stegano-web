from PIL import Image

# Message ko binary me convert karne ke liye
def message_to_bin(message):
    return ''.join(format(ord(char), '08b') for char in message)

# Binary ko text me convert karne ke liye
def bin_to_message(binary_data):
    message = ""
    
    # 8-8 bits me divide karo
    for i in range(0, len(binary_data), 8):
        byte = binary_data[i:i+8]
        
        # Agar 8 bits se kam ho to skip
        if len(byte) < 8:
            continue
            
        message += chr(int(byte, 2))
        
    return message

# Image me message hide karna
def encode_image(image_path, secret_message, output_path):
    try:
        img = Image.open(image_path)

        # RGB mode ensure karo
        if img.mode != 'RGB':
            img = img.convert('RGB')

        encoded_img = img.copy()
        width, height = img.size

        # Ending marker add karo
        secret_message += "##"

        # Binary me convert
        bin_secret_msg = message_to_bin(secret_message)
        data_len = len(bin_secret_msg)

        # Capacity check
        max_capacity = width * height * 3

        if data_len > max_capacity:
            print("Error: Message image me fit nahi ho sakta!")
            return

        data_index = 0
        pixels = encoded_img.load()

        # Pixels modify karo
        for y in range(height):
            for x in range(width):

                if data_index >= data_len:
                    break

                r, g, b = pixels[x, y]

                # Red channel
                if data_index < data_len:
                    r = (r & ~1) | int(bin_secret_msg[data_index])
                    data_index += 1

                # Green channel
                if data_index < data_len:
                    g = (g & ~1) | int(bin_secret_msg[data_index])
                    data_index += 1

                # Blue channel
                if data_index < data_len:
                    b = (b & ~1) | int(bin_secret_msg[data_index])
                    data_index += 1

                pixels[x, y] = (r, g, b)

            if data_index >= data_len:
                break

        encoded_img.save(output_path)

        print(f"\nMubarak ho! Message chhupa diya gaya hai.")
        print(f"Nayi image file: {output_path}")

    except FileNotFoundError:
        print(f"Error: '{image_path}' file nahi mili!")

    except Exception as e:
        print("Encoding Error:", e)

# Hidden message nikalna
def decode_image(image_path):
    try:
        img = Image.open(image_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        pixels = img.load()
        width, height = img.size

        binary_data = ""

        # Sare LSB bits read karo
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]

                binary_data += str(r & 1)
                binary_data += str(g & 1)
                binary_data += str(b & 1)

        decoded_message = ""

        # 8-bit chunks me convert
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i:i+8]

            if len(byte) < 8:
                continue

            decoded_message += chr(int(byte, 2))

            # End marker milte hi stop
            if decoded_message.endswith("##"):
                return decoded_message[:-2]

        return "Koi hidden message nahi mila!"

    except FileNotFoundError:
        return f"Error: '{image_path}' file nahi mili!"

    except Exception as e:
        return f"Decoding Error: {e}"

# Main Program
if __name__ == "__main__":

    # Secret message
    khufiya_msg = "Mission 4th Year: Steganography Project successfully running!"

    # Input aur output image
    input_image = "input.png"
    output_image = "secret_output.png"

    print("Encoding shuru ho raha hai...")

    # Encode
    encode_image(input_image, khufiya_msg, output_image)

    # Decode test
    print("\nAb image se message nikal rahe hain...")

    extracted_msg = decode_image(output_image)

    print("\nChhupa hua message mila:")
    print(extracted_msg)