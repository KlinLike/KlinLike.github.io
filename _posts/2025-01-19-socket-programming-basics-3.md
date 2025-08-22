---
layout: post
title:  "🌳对Socket基本用法的复习和理解 - Part 3"
date:   2025-01-19 17:22:42 +0800
tags: [socket, networking, programming, cpp]
---

# 前言
&nbsp;&nbsp;在 part 2 中弄明白了服务器代码的实现，这部分来关注客户端的部分，顺便补充一些碎片知识。

# int connect( SOCKET s, const sockaddr* name, int namelen)
&nbsp;&nbsp;函数功能：向服务器发起连接请求。
- 参数 s：客户端的套接字描述符，即客户端socket函数的返回值；
- 参数 name：要连接到服务器的信息；
- 参数 namelen：参数2的字节长度。

&nbsp;&nbsp;函数执行成功返回0，失败返回1。调用connect后，只有发生以下情况才会返回：
- 服务器接收连接请求；
- 发生断网等异常导致请求中断，如服务器的连接队列已满；
若因为异常无法连接，errno会被设置成特定错误，如 ECONNREFUSED 或 ETIMEOUT。

&nbsp;&nbsp;connect函数只是把连接请求发送给服务器，并将请求放入服务器的等待队列中。实际的数据交换要在服务器调用accept后才能开始。
&nbsp;&nbsp;但connect后，accept前客户端发送的数据不会丢失，是因为客户端有发送缓冲区，服务器也有接收缓冲区，数据不会被马上发送，服务器也有时间在调用accept创建套接字后再处理缓冲区中的数据。

# 简要示例代码
```
// 初始化Winsock
WSAData wsadata;
int fd = WSAStartup(MAKEWORD(2, 2), &wsadata);
if (fd != 0) {
    std::cerr << "Startup Error:" << fd << std::endl;
    return -1;
}

// 创建Socket
SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);
if (sock == INVALID_SOCKET) {
    std::cerr << "Create socket failed." << std::endl;
    WSACleanup();
    return -1;
}

// 设置服务器地址
sockaddr_in addr;
addr.sin_family = AF_INET;
inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr.s_addr);
addr.sin_port = htons(8888);
// Note: client不需要bind

// 连接到服务器
int conn_ret = connect(sock, (sockaddr*)&addr, sizeof(addr));
if (conn_ret == SOCKET_ERROR) {
    std::cerr << "Connection failed." << std::endl;
    closesocket(sock);
    WSACleanup();
    return -1;
}

// send
const char* msg = "OK?";
int send_ret = send(sock, msg, strlen(msg), 0);
if (send_ret == SOCKET_ERROR) {
    std::cerr << "Send failed." << std::endl;
    closesocket(sock);
    WSACleanup();
    return -1;
}

// recv
char buffer[1024];
int bytesReceived = recv(sock, buffer, sizeof(buffer) - 1, 0);
if (bytesReceived > 0) {
    // 正常接收到数据
    buffer[bytesReceived] = '\0';
    std::cout << "Received:" << buffer << std::endl;
}
else if (bytesReceived == 0) {
    // 服务器关闭连接
    std::cout << "Connection closed." << std::endl;
}
else {
    std::cerr << "Receive failed: " << bytesReceived << std::endl;
}

// 关闭清理
closesocket(sock);
WSACleanup();
return 0;
```

# 关于数据格式的转换
### 1. 字节序
&nbsp;&nbsp;计算机有两种储存数据的方式：大段字节序和小端字节序 ( Big Endian, Little Endian )。
&nbsp;&nbsp;大端指的是数据的高字节保存在内存的低地址中；小端指的是数据的高字节保存在内存的高地址中。
&nbsp;&nbsp;之所以有两种字节序共存，是因为计算机处理小端序的数据效率更高，所以计算机内部都是小端序。但人类习惯读写大端序，所以出了计算机内部处理，几乎所有场合都是大端序，如网络传输和文件存储。
&nbsp;&nbsp;因此，人们常说的网络字节序即大端字节序，主机字节序即小端字节序（和CPU有关，也不绝对，只是大多数时候是小端序）。
  *&nbsp;&nbsp;C++程序的字节序和编译平台所在的CPU相关，但JAVA唯一采用大端序，可见对字节序转换是有必要的。*

&nbsp;&nbsp;人习惯阅读的点分十进制表示的IP地址自然不分大小端序，但在计算内部以数值存储的IP地址可能会有大小端序之分。
- htonl()：Host to Network Long，将 32 位整数从主机字节序转换为网络字节序；
- htons()：Host to Network Short，将 16 位整数从主机字节序转换为网络字节序；
- ntohl()：Network to Host Long，将 32 位整数从网络字节序转换为主机字节序；
- ntohs()：Host to Network Short，将 16 位整数从网络字节序转换为主机字节序。
-> 32位用于IPV4地址，16位用于端口号。
-> 不同的后缀代表不同的处理数据格式，如htond将double类型的数据转换为网络字节序，htonll处理unsigned int64类型。

&nbsp;&nbsp;推荐使用 inet_pton 和 inet_ntop 代替 inet_aton 、 inet_ntoa 和 inet_addr ，区别在于它们支持IPV6、线程安全和错误处理机制更清晰。

&nbsp;&nbsp;hton和ntoh函数还是被推荐使用的，原因如下：
- 是POSIX标准的一部分，确保了在各种操作系统上的兼容性
- 简单直接
- 在许多系统上进行了高度优化，性能可靠

```
// 运行代码可以看到两种字节序的区别及了解转换函数的使用
void convert() {
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);

    const char* ipStr = "192.168.1.1";
    in_addr addr;
    inet_pton(AF_INET, ipStr, &addr);   // Internet presentation to network，点分十进制转换为网络字节序

    std::cout << "Network byte order:" << std::hex << addr.s_addr << std::endl;
    std::cout << "Host byte order:" << std::hex << ntohl(addr.s_addr) << std::endl;

    WSACleanup();
}
```

### 2. sockaddr结构体
&nbsp;&nbsp;sockaddr_in中的in代表internet，它弥补了sockaddr的缺陷，把端口号和目标地址分开存储在两个变量中。sockaddr_in是internet环境下套接字的地址形式，所以在网络编程中我们会对sockaddr_in结构体进行操作，使用sockaddr_in来建立所需的信息，最后使用强制类型转换为sockaddr用作参数。

### 3. 点分十进制转整数
&nbsp;&nbsp;把一个IPv4地址的每一段看作一个0~255的整数，先把每段拆分成一个二进制形式，然后把每段的数组合起来变成一个二进制形式的长整数，这就是把点分十进制转换为整数表示的方法。

&nbsp;&nbsp;以10.0.3.193这个IP地址为例：
10 -> 00001010
0 -> 00000000
3 -> 00000011
193 -> 11000001
&nbsp;&nbsp;组合起来即为：00001010 00000000 00000011 11000001，转换为十进制数就是：167773121，所以10.0.3.193这个IPv4地址转换为int就是167773121。

# SOCKET如何设置参数
&nbsp;&nbsp;以设置接收超时为例：
```
int timeout = 1000;
setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout));
```
-> 要看更详细的信息可以到这里 https://learn.microsoft.com/zh-cn/windows/win32/api/winsock2/nf-winsock2-setsockopt

&nbsp;&nbsp;如果recv()的第四个参数被设为了MSG_WAITALL，在阻塞模式下不接收到指定数目（也就是缓冲区的长度）的数据就不会返回，除非设置了超时时间，也就是说超时的优先级大于读取数目。
但即使超时时间未到，只要对方关闭了连接，recv会立即退出并返回已收到的数据。
