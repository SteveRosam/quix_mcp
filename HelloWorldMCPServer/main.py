import socket

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000       # Arbitrary non-privileged port

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"MCP server listening on {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            data = conn.recv(1024)
            if data:
                response = b'Hello World\n'
                conn.sendall(response)
