import socket
import threading
import json
import time

class Client:
    def __init__(self, search_port=10000, timeout=3):
        self.search_port = search_port  # 与服务器的搜索端口一致
        self.timeout = timeout  # 搜索超时时间（秒）
        self.servers = []  # 存储发现的服务器列表

    def search_servers(self):
        """发送UDP广播搜索服务器"""
        self.servers = []  # 清空历史列表
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 允许广播，设置超时
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.settimeout(1)  # 单次接收超时1秒

        # 发送搜索指令到局域网广播地址（覆盖常见子网）
        broadcast_addrs = [
            "255.255.255.255",  # 有限广播（可能被路由器限制）
            "192.168.1.255",    # 常见子网广播地址（根据实际网络调整）
            "192.168.0.255"
        ]
        search_msg = "SEARCH_SERVER"
        for addr in broadcast_addrs:
            udp_sock.sendto(search_msg.encode('utf-8'), (addr, self.search_port))

        # 等待服务器回复（超时时间内循环接收）
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                data, server_addr = udp_sock.recvfrom(1024)
                server_info = json.loads(data.decode('utf-8'))
                # 去重（避免同一服务器多次回复）
                if server_info not in self.servers:
                    self.servers.append(server_info)
                    print(f"发现服务器：{server_info['ip']}:{server_info['tcp_port']}")
            except socket.timeout:
                continue
        udp_sock.close()

    def connect_server(self, server_info):
        """连接指定服务器（TCP）"""
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((server_info['ip'], server_info['tcp_port']))
            print(f"已连接到服务器：{server_info['ip']}:{server_info['tcp_port']}")

            # 发送测试消息
            msg = "Hello, 我是客户端！"
            tcp_sock.send(msg.encode('utf-8'))
            print(f"发送消息：{msg}")

            # 接收回复
            response = tcp_sock.recv(1024).decode('utf-8')
            print(f"收到回复：{response}")
            tcp_sock.close()
        except Exception as e:
            print(f"连接失败：{e}")

    def start(self):
        """启动客户端：搜索并连接服务器"""
        print("开始搜索局域网内的服务器...")
        self.search_servers()

        if not self.servers:
            print("未发现任何服务器")
            return

        # 选择第一个服务器连接（可改为让用户选择）
        print("\n选择第一个服务器连接...")
        self.connect_server(self.servers[0])

if __name__ == "__main__":
    client = Client()
    client.start()