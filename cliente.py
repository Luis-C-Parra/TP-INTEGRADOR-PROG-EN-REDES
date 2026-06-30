import socket, threading, sys
from os import system

HOST, PORT = '127.0.0.1', 12345

def escuchar(sock):
    """Hilo que queda escuchando todo lo que manda el servidor y lo imprime en pantalla."""
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data:
                print("\n[SESIÓN CERRADA] El servidor finalizó la conexión.")
                break
            print(data, end="")
        except Exception:
            break
    print("\nPresioná Enter para salir.")
    sys.exit()

def lanzar_cliente():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception as e:
        return print(f"[ERROR] No se pudo conectar: {e}")

    # Pantalla de login, nada del otro mundo
    system("cls" if sys.platform.startswith("win") else "clear") #hace que la pantalla este limpia
    print("=== AUTENTICACIÓN - CHAT ===")
    usuario = input("Usuario: ").strip()
    password = input("Contraseña: ").strip()
    sock.sendall(f"{usuario},{password}".encode())  # mandamos las credenciales juntas separadas por coma

    resp = sock.recv(1024).decode()
    print(f"\n{resp}")
    if "RECHAZADO" in resp or "ERROR" in resp:
        return sock.close()  # si no le gusto el login, cerramos y listo

    # Una vez logueado, prendemos un hilo aparte solo para escuchar al servidor
    threading.Thread(target=escuchar, args=(sock,), daemon=True).start()

    print("Logueado. Escribí mensajes o comandos (/repos usuario, /followers usuario, /hora, /todos + mensaje, /usuarios, /adios)\n")
    while True:
        try:
            linea = input()
            if not linea.strip():
                continue  # si tira enter en vacio, no mandamos nada
            sock.sendall(linea.encode())
            if linea.strip() == "/adios":
                break  # si el usuario pide salir, cortamos el bucle
        except (KeyboardInterrupt, EOFError):
            # si lo cierra con Ctrl+C o asi, avisamos al server que nos vamos
            sock.sendall(b"/adios")
            break

    sock.close()
    print("Cliente finalizado.")

if __name__ == "__main__":
    lanzar_cliente()