---
title:  "🌱seq num 在握手阶段和传输阶段的不同含义"
date: 2025-08-06T18:33:14+08:00
tags: [tcp, networking, protocol, sequence-number]
---

最近在学习TCP协议栈，发现一个令人困惑的点：既然TCP头部中的seq num是已发送的数据长度，那三次握手中没有任何数据传输，seq num不应该增加才对，为什么也会增长呢？
查阅资料后我发现，原来在握手阶段和数据传输阶段，seq num有着不同的用处。
一句话总结：虽然在握手阶段没有应用层数据传输，但SYN包会在逻辑上消耗一个seq num序列号。

下面来详细拆解

# 握手阶段：不传输数据，但是会同步双方的初始序列号

### 第一次握手：
client发送一个报文，SYN为1。这个报文会设定一个初始序列号 seq = x。
这个报文的目的不是发送数据，而是告诉服务器：我要建立连接，我的序列号从x开始。
根据TCP协议的规定，SYN报文即使没有数据负载，也要占据一个序列号。

### 第二次握手
server收到client的SYN后，需要确认这个请求，所以回复 ack num = x + 1。
这个 x + 1 的含义是：我收到了你编号为x的SYN并确认无误，我期望下一个发送的字节序列号是 x + 1。
同时，服务器也发送自己的SYN，这个SYN的序列号是 seq num = y。

### 第三次握手
client收到server的 SYN + ACK 包，需要发送一个 ACK 来确认。
这个 ACK 的 seq num = x + 1， ack num = y + 1。

# 数据传输
握手完成，连接状态进入 ESTABLISHED 后，开始数据传输。
假设这时候client发送第一批数据，长度是 10 Byte：
client会从 seq = x + 1 开始发送数据，此时 seq = x + 1；
服务器成功收到 10 byte 的数据，需要回复一个 ACK。此时，ack = x + 11，含义是：我已经收到了包括 x + 10 在内的之前的全部字节，我期望下一次从 x + 11 开始发送。

# 流程图
最后附上一个流程图
![三次握手和数据传输]({{ site.baseurl }}/assets/images/2025-08-17-seq-num-meaning-in-handshake-and-transfer.png)
