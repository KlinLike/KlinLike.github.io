---
layout: post
title:  "🌳对Socket基本用法的复习和理解 - Part 2"
date:   2025-01-05 13:33:52 +0800
tags: [socket, networking, programming, cpp]
---

# 前言
&nbsp;&nbsp;本节的主要目标是在Windows平台上开始基本的socket编程，先简单实现服务器的部分。

# WSAStartup
&nbsp;&nbsp;要在Windows中进行socket编程，首先要用静态库Ws2_32.dll中的WSAStartup函数进行初始化。
&nbsp;&nbsp;*－＞静态库对应的头文件是WinSock2.h。*

&nbsp;&nbsp;WSAStartup的第一个参数为WORD类型的版本号，要使用宏函数MAKEWORD()生成，如MAKEWORD(1, 2)代表WinSock 1.2版本。
&nbsp;&nbsp;*－＞现在我们一般用2.2版本。*

&nbsp;&nbsp;WSAStartup的第二个参数为指向WSAData结构体的指针，这个参数用于回传关于Windows Socket的信息。

部分信息：
- wVersion：建议使用的版本号
- wHighVersion：支持最高版本号
- szDescription：ws2_32.dll的实现和厂商信息
- szSystemStatus：ws2_32.dll的状态和配置信息

&nbsp;&nbsp;调用WSAStartup初始化后，就可以开始socket编程了。

```
WSAData wsadata;
WSAStartup(MAKEWORD(2, 2), &wsadata);
```
# SOCKET socket(int af, int type, int protocol)
&nbsp;&nbsp;执行成功返回新的套接字描述符，失败返回INVALID_SOCKET。
&nbsp;&nbsp;*－＞返回-1请检查WSAStartup初始化是否成功。*

- 参数 af：表明协议族，常用的有AF_INET \ AF_INET6 \ AF_LOCAL，其中AF_INET即ipv4，计算比ipv6更快；
- 参数 type：表明socket类型，如SOCK_STREAM \ SOCK_DGRAM；
- 参数 protocol：表明传输协议。一般为0，因为系统会根据 af 和 type 推断，除非是某个 af 和 type 组合对应多重协议或自定协议，如 AF_INET 和 SOCK_RAW，可以是 IPPROTO_TCP 或 IPPROTO_UDP。

# int bind(SOCKET s, const sockaddr * addr, int addrlen)
&nbsp;&nbsp;bind将监听套接字绑定到本地地址和端口上，成功返回非负值，失败返回-1。
&nbsp;&nbsp;*－＞bind函数的作用可以理解为将抽象的socket与实际存在的计算机的某个网络端口绑定起来，软件可以通过这个抽象对象与实际的网络发生联系。*
&nbsp;&nbsp;*－＞一般来说客服端不需要调用bind，系统会自动分配ip和端口，但也有特殊情况。*

- 参数 s: 套接字描述符；
- 参数 addr：指向要分配给绑定套接字的本地地址的指针；
- 参数 addrlen：参数二指向结构体的字节长度。

```
    WSAData wsadata;
    int fd = WSAStartup(MAKEWORD(2, 2), &wsadata);

    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);

    sockaddr_in addr;
    addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr.s_addr); // 可以使用INADDR_ANY监听所有接口
    addr.sin_port = htons(8888);

    bind(sock, (sockaddr*)&addr, sizeof(addr));
```
# int listen( SOCKET s, int backlog)
&nbsp;&nbsp;调用listen可以让socket进入监听状态。
&nbsp;&nbsp;*－＞进入监听状态后，socket才会开始监听请求，也就是说，在这之后才会处理客户端的连接请求。*
&nbsp;&nbsp;*－＞注意函数功能描述是进入监听状态，而不是监听。*
&nbsp;&nbsp;*－＞函数执行成功返回0，失败返回错误码SOCKET_ERROR（可以用WSAGetLastError()获取更多错误信息，下面所有返回SOCKET_ERROR的函数都可以这样来查询错误信息）。*

- 参数 s： 依然是套接字描述符
- 参数 backlog： 用于指定接收队列的长度，即服务器在调用accept函数前最大允许进入连接的请求数，多余的请求将会被拒绝。典型值是5。

&nbsp;&nbsp;*参数backlog代表连接队列的长度。连接状态分为半连接和全连接，半连接是服务器已经收到了客户端的连接请求，但还没有完成三次握手；全连接是完成了三次握手，可以正常传输数据。如果新连接请求到达，而连接队列中处于全连接和半连接的连接数量已经达到了backlog，服务器不会接受这个请求，而是回复拒绝后直接丢弃。*

# int  accept( SOCKET s, const sockaddr * addr, int addrlen)
&nbsp;&nbsp;接受一个客服端的连接请求，默认如果没有请求会阻塞，如果有特殊需求（如性能需求）可以设置为非阻塞。
&nbsp;&nbsp;*－＞如果需要同时处理多个客户端的请求，可以在accept之后开子线程。*

- 返回值： 失败返回INVALID_SOCKET，成功返回SOCKET类型的值，是新的套接字，可以用来和刚accept的客户端通信。
- 参数 s： 同上；
- 参数 addr： 用于存储连接的客户端信息，是由函数外传的；
- 参数 addrlen：参数addr的字节大小，是in-out参数，传入值是addr指向区域的大小，传出的是已经填充了的大小。

# int recv( SOCKET s, char* buf, int len, int flags)
&nbsp;&nbsp;用于接收客户端或服务端传来的数据，即客户端和服务端都会使用。

- 返回值： 正常情况下返回收到的字节数，连接关闭返回0，异常情况返回SOCKET_ERROR；
- 参数s： 在服务端是accept函数的返回值、在客户端是connect函数的返回值，都是代表通信对象的socket；
- 参数 buf： 指向要存储接收数据所在缓冲区的地址；
- 参数 flags： 收发数据的附带标记，一般为0。

#####  常用的标记：
- MSG_DONTROUTE :  不使用路由表查找路由，而是直接发送包到指定接口，常用于局域网或确信无需转发的时候。对send、sendto有效；
- MSG_PEEK： 查看socket接收缓冲区中的数据，但不会清除这些数据，常用于在正式读取前预先了解缓冲区中的数据。对recv、recvfrom有效；
- MSG_OOB： 发送或接收加急数据，即带外数据（out-of-band），常用于控制命令或紧急通知，对收发函数都有效。
*如果有多个标志叠加，需要使用按位or。*

##### 关于带外数据OOB
&nbsp;&nbsp;使用和常规数据一样的发送路径，通过处理方式实现的“加急”。
1. 使用 TCP header 中的紧急指针 urgent pointer 来标记数据流中紧急数据的位置，其指向数据的最后一个字节。
2. 使用 TCP header 中的 URG（urgent）标志位标记。
  &nbsp;&nbsp;接收方在收到带有URG标记的数据包时，会优先处理。TCP会立即将其传递给应用层，即使常规数据还没有处理完。操作系统会通过API通知应用，使得应用可以立即处理（这也是为什么MSG_OOB可以用于读取函数，在收到通知后，可以立即读取紧急信息）。

# int send（ SOCKET s， const char* buf， int len， int flags)
&nbsp;&nbsp;向通信的对方发送数据。

- 返回值：无异常则返回已经发送了的字节数（可能会小于请求发送的字节数），否则返回SOCKET_ERROR；
- 参数 s： 同上，是已连接的socket；
- 参数 buf：指向要发送数据的指针；
- 参数 len： 要发送的数据的长度；
- 参数 flags：同recv的参数flags。

# int closesocket（SOCKET s）
&nbsp;&nbsp;关闭套接字，包括释放资源和断开连接。
&nbsp;&nbsp;*－＞TCP的四次挥手操作就是closesocket函数触发的。*

- 返回值： 正常情况下返回0，否则返回SOCKET_ERROR；
- 参数 s： 同上，是需要关闭的socket。

# int WSACleanup()
&nbsp;&nbsp;可以理解为是WSAStartup反向操作，结束对Ws2_32.dll的使用。

&nbsp;&nbsp;返回值： 操作成功会返回0，失败返回SOCKET_ERROR。

&nbsp;&nbsp;在多线程环境中，WSACleanup将终止整个进程的Winsock库，而不只是当前线程的，需要小心使用。

# 简单的服务器示例代码
```
#include <iostream>
#include <WinSock2.h>
#include <WS2tcpip.h>
#pragma comment(lib, "ws2_32.lib")


int func() {
    // 准备工作
    WSAData wsadata;
    int fd = WSAStartup(MAKEWORD(2, 2), &wsadata);
    if (fd != 0) {
        std::cerr << "Startup Error:" << fd << std::endl;
        return -1;
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);

    sockaddr_in addr;
    addr.sin_family = AF_INET;
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr.s_addr);
    addr.sin_port = htons(8888);

    bind(sock, (sockaddr*)&addr, sizeof(addr));

    listen(sock, 5);

    sockaddr_in client;
    int len = sizeof(client);
    auto client_sock = accept(sock, (sockaddr*)&client, &len);

    // 从客户端接收数据
    char recv_buffer[1024];
    int recv_result = recv(client_sock, recv_buffer, sizeof(recv_buffer) - 1, 0);
    if (recv_result == SOCKET_ERROR) {
        std::cerr << "Recv Error:" << WSAGetLastError() << std::endl;
        closesocket(client_sock);
        closesocket(sock);
        WSACleanup();
        return -1;
    }
    else if (recv_result == 0) {
        std::cout << "connection closed." << std::endl;
        closesocket(client_sock);
        closesocket(sock);
        WSACleanup();
        return -1;
    }
    else {
        recv_buffer[recv_result - 1] = '\0';
        std::cout << "Recv:" << recv_buffer << std::endl;
    }

    // 向客户端发送数据
    std::string response = "OK";
    int send_result = send(client_sock, response.c_str(), response.length(), 0);
    if (send_result == SOCKET_ERROR) {
        std::cerr << "Send Error:" << WSAGetLastError() << std::endl;
        closesocket(client_sock);
        closesocket(sock);
        WSACleanup();
        return -1;
    }

    // 结束通信
    closesocket(client_sock);
    closesocket(sock);
    WSACleanup();
    return 0;
}
```


参考资料：https://learn.microsoft.com/zh-cn/windows/win32/api/_winsock/，很好用的网站，可以按需搜索对应的函数。