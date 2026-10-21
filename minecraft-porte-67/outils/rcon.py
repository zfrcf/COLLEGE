import socket, struct, sys
class Rcon:
    def __init__(s, host="127.0.0.1", port=25575, pw="test"):
        s.s = socket.create_connection((host, port)); s.id = 0
        s._send(3, pw); s._recv()
    def _send(s, t, body):
        s.id += 1
        d = struct.pack("<ii", s.id, t) + body.encode() + b"\0\0"
        s.s.sendall(struct.pack("<i", len(d)) + d)
    def _recvn(s, n):
        b = b""
        while len(b) < n:
            c = s.s.recv(n - len(b))
            if not c: raise EOFError
            b += c
        return b
    def _recv(s):
        n, = struct.unpack("<i", s._recvn(4)); d = s._recvn(n)
        return d[8:-2].decode(errors="replace")
    def cmd(s, c):
        s._send(2, c); return s._recv()
if __name__ == "__main__":
    r = Rcon()
    for c in sys.argv[1:]: print(r.cmd(c))
