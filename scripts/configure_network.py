import socket
import ipaddress
import os
import sys
import subprocess
import platform

def get_local_ip():
    """Obtiene la IP local de la máquina de forma segura"""
    try:
        # Crear una conexión UDP para obtener la IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None

def validate_ip(ip):
    """Valida que la IP sea válida y segura"""
    try:
        # Validar formato de IP
        ip_obj = ipaddress.ip_address(ip)
        
        # Verificar que no sea una IP privada especial
        if ip_obj.is_loopback:
            print("Advertencia: La IP es una dirección de loopback")
            return False
        if ip_obj.is_multicast:
            print("Error: No se permiten IPs multicast")
            return False
        if ip_obj.is_unspecified:
            print("Error: IP no especificada")
            print("Advertencia: La IP es una dirección de loopback")
            return False
        if ip_obj.is_multicast:
            print("Error: No se permiten IPs multicast")
            return False
        if ip_obj.is_unspecified:
            print("Error: IP no especificada")

            return False
            
        # Verificar que la IP pertenezca a la red local
        if not ip_obj.is_private:
            print("Advertencia: La IP no es una dirección privada")
            return False
            
        return True
    except ValueError:
        print("Error: IP inválida")
        return False

def check_port_availability(ip, ports):
    """Verifica que los puertos necesarios estén disponibles"""
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((ip, port))
            sock.close()
        except socket.error:
            print(f"Error: El puerto {port} ya está en uso")
            return False
    return True

def check_ngrok_token():
    """Verifica si el token de ngrok está configurado"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    with open(env_path, 'r') as f:
        content = f.read()
        
    if 'NGROK_AUTHTOKEN=' in content and not content.split('NGROK_AUTHTOKEN=')[1].split('\n')[0].strip():
        print("NGROK_AUTHTOKEN no está configurado en el archivo .env")
        token = input("Por favor, ingresa tu token de ngrok (regístrate en https://ngrok.com): ").strip()
        
        if token:
            content = content.replace('NGROK_AUTHTOKEN=', f'NGROK_AUTHTOKEN={token}')
            with open(env_path, 'w') as f:
                f.write(content)
            return True
        return False
    return True

def configure_network():
    """Configura la red de forma segura"""
    # Verificar token de ngrok
    if not check_ngrok_token():
        print("Error: Se requiere un token de ngrok para el acceso remoto")
        return False

    # Detectar IP local
    local_ip = get_local_ip()
    if not local_ip:
        print("Error: No se pudo detectar la IP local")
        return False

    print(f"IP local detectada: {local_ip}")
    
    # Validar IP
    if not validate_ip(local_ip):
        print("Error: La IP detectada no es válida para uso")
        return False
        
    # Verificar puertos
    required_ports = [5173, 8000, 9000, 9001]
    if not check_port_availability(local_ip, required_ports):
        print("Error: Algunos puertos requeridos no están disponibles")
        return False

    # Actualizar archivo .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    with open(env_path, 'r') as f:
        env_content = f.read()

    # Actualizar HOST_IP
    env_content = env_content.replace('HOST_IP=0.0.0.0', f'HOST_IP={local_ip}')
    
    # Actualizar ALLOWED_ORIGINS
    allowed_origins = f'http://{local_ip}:5173,http://localhost:5173,http://127.0.0.1:5173'
    env_content = env_content.replace('ALLOWED_ORIGINS=', f'ALLOWED_ORIGINS={allowed_origins}')

    with open(env_path, 'w') as f:
        f.write(env_content)

    print(f"""
   Configuración de red completada:
   - IP: {local_ip}
   - Puertos: {required_ports}
   - Archivo .env actualizado

   Recomendaciones de seguridad:
   1. Configura tu firewall para permitir solo los puertos necesarios
   2. Utiliza HTTPS en producción
   3. Limita el acceso a las IPs de tu red local
   4. Monitorea el tráfico de red regularmente
""")
    return True

if __name__ == "__main__":
    if not configure_network():
        sys.exit(1)