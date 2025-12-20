---
layout: post
title:  "🌱浅谈WS协议的连接、传输和断开"
date:   2025-12-20 15:09:32 +0800
tags: [websocket, protocol, network]
---

## 建立连接

假设是客户端主动发起连接。

### 发起

在应用层 (WS/HTTP) 介入前，先建立传输层 TCP 连接，完成三次握手。
然后，客户端发送一个包含特殊 Header 的 HTTP GET 请求:

```http
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

- `Connection: Upgrade`, `Upgrade: websocket` 两个头告诉服务器要升级到 WebSocket 协议。
- `Sec-WebSocket-Key` 是随机生成的 Base64 字符串，为了防止代理服务器错误地缓存这个链接，同时确认服务器支持 WS。

## 响应

服务器收到请求后，如果同意升级，会返回 HTTP 101:

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

为了证明服务器确实支持 WS 协议，这里返回的 `Sec-WebSocket-Accept` 是需要计算的，不能只是简单 echo。

计算方法：
1. 取出客户端的 `Key`
2. 拼接上固定的 GUID
3. 对拼接后的字符进行 SHA-1
4. 对哈希值进行 Base64 编码

## 数据传输

一旦 101 响应被客户端接收并验证通过，双方就不在遵守 HTTP 协议，而是直接就底层的 TCP Socket 收发 WebSocket Frames。

WebSocket 的数据不像 HTTP 那样是纯文本流，而是被切分成帧:
- **Opcode**:　定义这一帧是文本、二进制、ping、pong 还是关闭连接
- **Masking**:　客户端发给服务器的数据要进行 Masking (为了防止被攻击)，但服务器发给客户端的数据通常不需要 Masking。

### 发送文本

连接建立后，如果发送“你好”，这个文本内容会如何被传输呢？
显然，WS不会简单地将字符串扔进 TCP 管道，而是将其封装成一个符合 RFC 6455 标准的数据帧。

#### Encoding
WebSocket 协议规定，文本帧必须用 UTF-8 编码。

- “你” 的 UTF-8 编码是：`0xE4 0xBD 0xA0`
- “好” 的 UTF-8 编码是：`0xE5 0xA5 0xBD`
- 总字节长度：6 字节。

#### Frame Header
WebSocket 帧由固定长度的头部和后续的载荷组成。

一个典型的短消息帧结构如下：

| 字段 | 长度 | 说明 | “你好” 对应的取值 |
| --- | --- | --- | --- |
| FIN | 1 bit | 是否是最后一个分片 | 1 (消息短，一个帧就发完了) |
| RSV1-3 | 3 bits | 保留位 | 000 |
| Opcode | 4 bits | 操作码 | 0x1 (表示这是一个文本帧) |
| Mask | 1 bit | 是否掩码处理 | 1 (客户端发给服务器必须为 1) |
| Payload len | 7 bits | 载荷长度 | 0000110 (十进制 6) |
| Masking-key | 32 bits | 掩码密钥 | 随机生成的 4 字节，例如 `0x12 0x34 0x56 0x78` |

#### Masking
客户端发送的所有数据都必须经过掩码处理，算法很简单，就是将原始数据的字节与掩码的字节进行 XOR 运算。

#### 最终传输的二进制流
所以，当发送“你好”的时候，最终传输的 16 进制序列是这样的：

`81 86 [Mask Key] [Masked Payload]`

- `81`: `1000 0001` (FIN=1, Opcode=1)
- `86`: `1000 0110` (Mask=1, Length=6)

### Opcode

| Opcode (Hex) | 名称 | 类型 | 含义 |
| --- | --- | --- | --- |
| 0x0 | Continuation | 数据帧 | 延续帧：用于分片消息。表示该帧是之前某个分片消息的后续部分。 |
| 0x1 | Text | 数据帧 | 文本帧：表示载荷数据是 UTF-8 编码的文本。 |
| 0x2 | Binary | 数据帧 | 二进制帧：表示载荷是原始二进制数据（如图片、音频、文件等）。 |
| | | | |
| 0x8 | Close | 控制帧 | 关闭帧：用于关闭连接。可以包含关闭状态码（如 1000 表示正常关闭）。 |
| 0x9 | Ping | 控制帧 | Ping 帧：心跳包。用来检测对方是否在线。 |
| 0xA | Pong | 控制帧 | Pong 帧：对 Ping 帧的响应。收到 Ping 后必须尽快回复 Pong。 |

- **无长度限制切片**：如果发送超大文件 (如 1GB), WebSocket 可以把数据切成多个帧，第一个帧 FIN=0， Opcode=2， 中间帧 FIN=0, Opcode=0 (延续帧)， 最后一帧 FIN=1, Opcode=0。
- 协议内置了 Ping (Opcode 0x9) 和 Pong (Opcode 0xA) 帧，用来在没有业务数据的时候检测连接是否断开。

## 关闭连接

1. 发起方发送关闭帧 (Opcode=0x8)，然后进入半关闭状态：不再发送新的业务数据，但任然必须接收对方可能还在路上的剩余数据
2. 响应方收到关闭帧后，如果有没发完的数据，可以尝试发完（非强制），然后必须尽快回发一个关闭帧进行确认
3. 收到确认关闭帧后，底层 TCP 连接正式关闭

- 关闭状态码放在 Payload 的前两个字节，紧随状态码后可以加上 UTF-8 文本，解释关闭原因。
- 关闭帧 Payload 和正常其他通信一样：如果是客户端发送的，必须进行 Masking；如果是服务器发送的，一定不能 Masking。
- WebSocket 允许发送没有载荷的关闭帧 (Payload=0)，但帧头的 Mask 还是需要设为 1，还是需要提供随机生成的 Masking-key。

## 为什么 Masking 可以避免代理服务器缓存

简单来说，Masking 不是为了加密，而是为了混淆。

在互联网中，客户端和服务器之间往往会存在很多透明代理和中转网关。这些代理服务器会试图识别每一个 HTTP 请求，如果发现是 GET 请求，可能会缓存这个 HTTP GET 请求对应的响应内容（缓存毒化）。

在引入了 Masking 之后，即使发送的是相同的 GET 字符串，但因为 Masking 的存在，每个字节都被随机的 Masking-key 异或了一次，所以代理服务器无法识别出这是一个 GET 请求（也无法识别出这是一个 HTTP 请求）。这样代理服务器自然就不会缓存这些请求了，这就是 Masking 存在的目的。

> 从这个角度看，也解释了为什么服务器不用 Masking：因为只要代理认不出来是 HTTP 请求，自然不会缓存服务器返回的内容，服务器发出的数据不进行 Masking 还能节省性能。尽管还有缓存毒化攻击的关系，但那不在这个文章的讨论范围内。
