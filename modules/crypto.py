"""
Módulo de Criptografía - C2 Project
====================================
Implementa encriptación AES para comunicación segura.
Solo para fines educativos en entornos controlados.
"""

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib


class AESCipher:
    """Clase para encriptación AES-256"""
    
    def __init__(self, key: bytes = None):
        """
        Inicializa el cifrador AES.
        
        Args:
            key: Clave de encriptación (si es None, se genera una aleatoria)
        """
        if key is None:
            self.key = get_random_bytes(32)  # AES-256
        else:
            # Derivar una clave de 32 bytes usando SHA-256
            self.key = hashlib.sha256(key).digest()
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encripta datos usando AES-CBC.
        
        Args:
            plaintext: Datos a encriptar
            
        Returns:
            bytes: IV + datos encriptados (base64)
        """
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        # Retornar IV + ciphertext en base64
        return base64.b64encode(iv + ciphertext)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Desencripta datos usando AES-CBC.
        
        Args:
            encrypted_data: Datos encriptados (IV + ciphertext en base64)
            
        Returns:
            bytes: Datos originales
        """
        # Decodificar base64
        raw = base64.b64decode(encrypted_data)
        # Extraer IV (primeros 16 bytes)
        iv = raw[:16]
        ciphertext = raw[16:]
        # Desencriptar
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return plaintext
    
    def encrypt_string(self, text: str) -> str:
        """Encripta un string y retorna base64"""
        encrypted = self.encrypt(text.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Desencripta un string desde base64"""
        decrypted = self.decrypt(encrypted_text.encode('utf-8'))
        return decrypted.decode('utf-8')


class XORCipher:
    """Cifrado XOR simple (para demostración educativa)"""
    
    def __init__(self, key: int = 0x42):
        self.key = key
    
    def encrypt(self, data: bytes) -> bytes:
        return bytes([b ^ self.key for b in data])
    
    def decrypt(self, data: bytes) -> bytes:
        return self.encrypt(data)  # XOR es simétrico


def generate_key() -> str:
    """Genera una clave aleatoria para AES"""
    return get_random_bytes(32).hex()


def derive_key(password: str) -> bytes:
    """Deriva una clave desde una contraseña usando SHA-256"""
    return hashlib.sha256(password.encode('utf-8')).digest()


# Ejemplo de uso
if __name__ == '__main__':
    print("=== Prueba de Criptografía ===\n")
    
    # AES
    print("[AES-256]")
    aes = AESCipher(b'mi_clave_secreta_123')
    mensaje = "Hola, esto es un mensaje secreto!"
    encriptado = aes.encrypt_string(mensaje)
    desencriptado = aes.decrypt_string(encriptado)
    
    print(f"Original: {mensaje}")
    print(f"Encriptado: {encriptado[:50]}...")
    print(f"Desencriptado: {desencriptado}")
    print(f"✓ Coincide: {mensaje == desencriptado}\n")
    
    # XOR
    print("[XOR Simple]")
    xor = XORCipher(0x42)
    datos = b"Mensaje XOR"
    encriptado_xor = xor.encrypt(datos)
    desencriptado_xor = xor.decrypt(encriptado_xor)
    
    print(f"Original: {datos}")
    print(f"Encriptado: {encriptado_xor}")
    print(f"Desencriptado: {desencriptado_xor}")
    print(f"✓ Coincide: {datos == desencriptado_xor}")
