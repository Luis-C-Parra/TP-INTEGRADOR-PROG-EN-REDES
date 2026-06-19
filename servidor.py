import socket
import threading
import mysql.connector
import requests
from datetime import datetime

# Datos del server: IP local y puerto donde escuchamos
HOST, PORT = '127.0.0.1', 12345

# Aca guardamos quien esta conectado: socket -> nombre de usuario
clientes = {}
lock = threading.Lock()  # esto es pa' que dos hilos no pisen el diccionario al mismo tiempo

def db():
    """Abre una conexion nueva a la base 'sockets' en MySQL Workbench."""
    return mysql.connector.connect(host='localhost', user='root', password='fabfab',
                                    database='sockets', port=3306)

def validar_usuario(usuario, password):
    """Chequea en la tabla 'usuarios' si el usuario y la clave son correctos."""
    try:
        cn = db(); cur = cn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE nombre=%s AND password=%s", (usuario, password))
        ok = cur.fetchone() is not None  # si encontro algo, esta todo bien
        cur.close(); cn.close()
        return ok
    except mysql.connector.Error as e:
        print(f"[DB ERROR] {e}")
        return False

def guardar_github(usuario_git, endpoint, tabla, campos):
    """
    Le pega a la API de GitHub (repos o followers, segun el endpoint)
    y guarda lo que devuelve en la tabla correspondiente de la base.
    """
    try:
        r = requests.get(f"https://api.github.com/users/{usuario_git}/{endpoint}")
        if r.status_code != 200:
            return -1  # algo salio mal con la API
        items = r.json()
        cn = db(); cur = cn.cursor()
        for it in items:
            valores = [usuario_git] + [it[c] for c in campos]
            placeholders = ", ".join(["%s"] * len(valores))
            cur.execute(f"INSERT INTO {tabla} VALUES (DEFAULT, {placeholders})", valores)
        cn.commit(); cur.close(); cn.close()
        return len(items)  # devolvemos cuantos guardamos
    except Exception as e:
        print(f"[API/DB ERROR] {e}")
        return -1

def broadcast(msg, origen):
    """Manda un mensaje a TODOS los clientes conectados (comando /todos)."""
    with lock:
        user = clientes.get(origen, "Anónimo")
        for sock in list(clientes):
            try:
                sock.sendall(f"\n[GLOBAL] {user}: {msg}\n".encode())
            except Exception:
                pass  # si algun socket esta roto, lo ignoramos y seguimos

def manejar_cliente(conn, addr):
    """Esta funcion corre en un hilo por cada cliente que se conecta."""
    print(f"[CONEXIÓN] Nuevo cliente conectado desde {addr}")
    usuario = None
    try:
        # Lo primero que esperamos es "usuario,password"
        creds = conn.recv(1024).decode().strip()
        if ',' not in creds:
            return conn.sendall(b"ERROR: formato de login invalido.\n")

        usuario, password = creds.split(',', 1)
        if not validar_usuario(usuario, password):
            return conn.sendall(b"RECHAZADO: usuario o contrasena incorrectos.\n")

        # Si llego hasta aca, esta logueado: lo metemos en la lista de activos
        with lock:
            clientes[conn] = usuario
        conn.sendall(f"ACEPTADO: Bienvenido, {usuario}!\n".encode())

        # Bucle infinito escuchando lo que manda el cliente
        while True:
            data = conn.recv(1024)
            if not data:
                break  # el cliente se desconecto sin avisar
            msg = data.decode().strip()

            if msg.startswith('/'):
                # Es un comando, lo separamos en comando + argumento
                partes = msg.split(' ', 1)
                cmd, arg = partes[0], (partes[1].strip() if len(partes) > 1 else "")

                if cmd == "/adios":
                    conn.sendall(b"Sesion terminada!\n")
                    break
                elif cmd == "/hora":
                    conn.sendall(f"[SERVIDOR] {datetime.now().strftime('%H:%M:%S')}\n".encode())
                elif cmd == "/usuarios":
                    with lock:
                        lista = ", ".join(clientes.values())
                    conn.sendall(f"[SERVIDOR] Conectados: {lista}\n".encode())
                elif cmd == "/repos":
                    if not arg:
                        conn.sendall(b"[ERROR] Uso: /repos usuario_github\n")
                    else:
                        conn.sendall(b"[SERVIDOR] Consultando GitHub...\n")
                        n = guardar_github(arg, "repos", "repositorios", ["name", "html_url"])
                        conn.sendall((f"[SERVIDOR] {n} repos guardados de '{arg}'.\n" if n >= 0
                                      else "[ERROR] Fallo al consultar repos.\n").encode())
                elif cmd == "/followers":
                    if not arg:
                        conn.sendall(b"[ERROR] Uso: /followers usuario_github\n")
                    else:
                        conn.sendall(b"[SERVIDOR] Consultando GitHub...\n")
                        n = guardar_github(arg, "followers", "followers", ["login", "html_url"])
                        conn.sendall((f"[SERVIDOR] {n} followers guardados de '{arg}'.\n" if n >= 0
                                      else "[ERROR] Fallo al consultar followers.\n").encode())
                elif cmd == "/todos":
                    if not arg:
                        conn.sendall(b"[ERROR] Uso: /todos mensaje\n")
                    else:
                        broadcast(arg, conn)
                else:
                    conn.sendall(b"[SERVIDOR] Comando no reconocido.\n")
            else:
                # No es comando, es chat normal: lo mostramos y le mandamos un eco
                print(f"[{usuario}]: {msg}")
                conn.sendall(f"[SERVIDOR-ECO] '{msg}'\n".encode())
    except Exception as e:
        print(f"[ALERTA] {addr}: {e}")
    finally:
        # Pase lo que pase, lo sacamos de la lista de activos y cerramos el socket
        with lock:
            clientes.pop(conn, None)
        conn.close()
        print(f"[DESCONEXIÓN] El Usuario {usuario} se retiro del chat.")

def iniciar_servidor():
    """Levanta el socket del servidor y queda esperando conexiones pa' siempre."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # pa' poder reusar el puerto rapido
    server.bind((HOST, PORT))
    server.listen(15)  # cola de hasta 15 conexiones esperando
    print(f"[*] Servidor activo en {HOST}:{PORT}")
    try:
        while True:
            conn, addr = server.accept()  # se queda frenado hasta que llegue alguien
            # cada cliente nuevo se atiende en su propio hilo, asi no se bloquean entre si
            threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[*] Apagando servidor.")
    finally:
        server.close()

if __name__ == "__main__":
    iniciar_servidor()