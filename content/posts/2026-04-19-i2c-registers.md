---
title: "STM32 I2C寄存器详解"
date: 2026-04-19T13:43:40+08:00
categories: [系统与性能]
tags: [embedded, i2c, c]
draft: false
---

## 寄存器

下面说明一下STM32 I2C硬件内部的核心寄存器。

### CR1 - Control Register 1 - 控制寄存器1

功能：主控制，启动/停止I2C操作、使能各种功能。

最常用的四个位：

| 位 | 全称 | 功能 |
|------|------|------|
| PE | Peripheral Enable | I2C模块使能 |
| START | Start Generation | 设置=1，发送Start信号 |
| STOP | Stop Generation | 设置=1，发送Stop信号 |
| ACK | Acknowledge Enable | 使能ACK响应（读数据时要=1）|

### CR2 - Control Register 2 - 控制寄存器2

功能：配置中断、DMA、时钟源

| 位 | 全称 | 功能 |
|------|------|------|
| ITERREN | Error Interrupt Enable | 错误中断使能 |
| ITEVTEN | Event Interrupt Enable | 事件中断使能（SB、ADDR、TXE等）|
| ITBUFEN | Buffer Interrupt Enable | 缓冲中断使能（TXE、RXNE）|
| DMAEN | DMA Enable | DMA使能 |

中断使能的3个位：

- ITERREN：错误时触发中断（ACK失败、超时等）
- ITEVTEN：事件时触发中断（Start发送完、地址发送完等）
- ITBUFEN：缓冲区时触发中断（发送空、接收满）

### CCR - Clock Control Register - 时钟控制寄存器

功能：设置SCL时钟频率

寄存器的核心有三个：

| 位 | 全称 | 功能 |
|------|------|------|
| F/S | Fast/Standard Mode | 0=标准100kHz，1=快速400kHz |
| CCR | Clock Control Register | SCL周期 = CCR × T基准 |
| DUTY | 快速模式占空比 | 0: Tlow:Thigh=2:1，1: Tlow:Thigh=16:9 |

先理解基本概念：

| 符号 | 含义 |
|------|------|
| Tpclk1 | PCLK1时钟周期（STM32的I2C时钟源）|
| Thigh | SCL高电平时间 |
| Tlow | SCL低电平时间 |

在标准模式下：

一个完整的SCL时钟周期 = Tlow + Thigh
CCR决定了每个时间有多长：

```text
Tlow = CCR × Tpclk1
Thigh = CCR × Tpclk1
```

所以：
周期 = Tlow + Thigh = 2 × CCR × Tpclk1

但以上公式只有在标准模式生效，如果F/S被设为了1，也就是快速模式，因为占空比不同（DUTY），有不同的计算方式。

在快速模式下：

```text
若 DUTY = 0 (Tlow:Thigh = 2:1)：
Thigh = 1 × CCR × Tpclk1
Tlow  = 2 × CCR × Tpclk1
─────────────────────
周期  = 3 × CCR × Tpclk1

若 DUTY = 1 (Tlow:Thigh = 16:9)：
Thigh = 9  × CCR × Tpclk1
Tlow  = 16 × CCR × Tpclk1
─────────────────────
周期  = 25 × CCR × Tpclk1
```

->快速模式有额外的占空比控制。

之所以会这样设计，我觉得本质原因是因为系统时钟频率远大于IIC的通信频率。
用打拍子比喻：

| 比喻 | 说明 |
|------|------|
| 系统时钟 | 心跳很快（36MHz = 每秒 3600 万次）|
| I2C 时钟 | 打拍子很慢（100kHz = 每秒 100 次）|
| CCR | 数多少次心跳打一下拍子 |

CCR 的本质：

```text
系统时钟（36MHz）────→ 计数器
                        │
                        ↓ 数 CCR 个周期
                        │
                        ↓ 翻转一次 SCL

CCR = "数多少个时钟周期后翻转"
```

所以本质上是多少个系统时钟周期走一个IIC SCL周期，占空比和快速/标准又会影响到一个SCL周期内有多少个CCR（快速3个，标准2个）。

明白了这个，我们很容易就知道应该怎么计算CCR了：
如果PCLK1是36MHz，而想有100kHz的时钟频率，就应该在CCR内写180。
如果我们想有400kHz的频率呢？
一个周期 = 一次完整的"高电平 + 低电平"
因为占空比变化了，周期 = 3 × CCR × Tpclk1

```text
CCR = 36M / (400k × 3)
    = 36,000,000 / 1,200,000
    = 30
```

不同系统的时钟频率不同，所以需要设置不同的CCR值来达到目标频率。比如如果目标都是100kHz：

| PCLK1频率 | 需要的CCR值 |
|-----------|------------|
| 8MHz | 40 |
| 36MHz | 180 |
| 72MHz | 360 |

那么问题来了，既然知道目标频率+时钟频率，就能算出CCR，为什么还要多此一举设置一个CCR寄存器呢？直接用F/S=0/1来设置不就好了吗？

答案是，实际的频率不是只有两种，CCR可以填任何值来灵活调整IIC频率，只要从设备支持就行。
所以，技术上说，是能在100kHz的频率下跑快速模式的。只是，这样是违反协议的，也会有时序不匹配的问题，而且没必要。用什么频率，就选择对应的模式，按照标准公式配置CCR就可以了。

而且，我们也不用死记这个公式，CubeMX在配置的时候，会自动计算。

### SR1 - Status Register 1 - 状态寄存器1

功能：显示当前操作状态（最重要的状态位）

最常用的5个位：

| 位 | 全称 | 功能 |
|------|------|------|
| SB | Start Bit | Start已发送，等待写地址 |
| ADDR | Address Sent | 地址已发送，等待清除 |
| TXE | Transmit Buffer Empty | 发送缓冲区空，可写下一个数据 |
| RXNE | Receive Buffer Not Empty | 接收缓冲区不空，读到数据了 |
| AF | Acknowledge Failure | ACK失败，从设备没响应 |

状态位含义：
- SB=1 → Start信号发完了，该写地址到DR
- ADDR=1 → 地址发完了，该读SR1+SR2清除它
- TXE=1 → 数据发完了，该写下一个数据到DR
- RXNE=1 → 收到数据了，该读DR取出数据
- AF=1 → 从设备没回ACK，通信失败

### SR2 - Status Register 2 - 状态寄存器2

功能：补充状态信息，读取后会自动清除SR1的某些位

最常用的3个位：

| 位 | 全称 | 功能 |
|------|------|------|
| MSL | Master/Slave | 1=主模式，0=从模式 |
| BUSY | Bus Busy | 总线忙（检测到Start或地址），实际上从Start到Stop，BUSY都=1 |
| TRA | Transmitter/Receiver | 1=发送，0=接收 |

清除ADDR的方法：
发地址后ADDR=1，必须清除才能继续
清除方法：先读SR1，再读SR2

```c
tmp = I2C1->SR1; // 读SR1
tmp = I2C1->SR2; // 读SR2（自动清除ADDR）
```

### DR - Data Register - 数据寄存器

功能：发送/接收数据的缓冲区

- 写入DR → 发送数据（数据进入发送缓冲区，硬件自动逐位发出）
- 读取DR → 接收数据（从接收缓冲区读取收到的数据）

注意：
- 写入DR后，硬件自动发送，不用管时序
- 读取DR后，RXNE自动清除
- DR和移位寄存器分开，可双缓冲

看干巴巴的说明会很抽象，下面我们整合 SR1 + SR2 + DR 到一个完整的流程里说明：

```text
┌─────────────────────────────────────────────────────────────┐
│                    STM32 作为主机读取从机                    │
└─────────────────────────────────────────────────────────────┘

步骤 1: 发送 Start
─────────────────────────
你的代码: I2C_GenerateSTART(I2C1, ENABLE);

硬件动作: SDA ↓ + SCL ↓ = Start 信号

SR1: SB=1 (Start 已发送)
SR2: BUSY=1, MSL=1 (总线忙，主模式)
DR:  无变化

你的动作: 检测 SR1.SB=1
          → 写地址到 DR


步骤 2: 写设备地址
─────────────────────────
你的代码: I2C_Send7bitAddress(I2C1, 0x48, I2C_Direction_Receiver);

硬件动作: 把 DR 内容逐位发送到总线
          从机返回 ACK

SR1: SB=0(自动清除), ADDR=1 (地址已发送且收到ACK)
SR2: BUSY=1, MSL=1, TRA=0 (接收模式)
DR:  空，准备接收

你的动作: 检测 SR1.ADDR=1
          → 读 SR1 → 读 SR2 (清除 ADDR)
```

TRA位由地址字节的R/W位决定：
发送地址时，最后一个bit：
- 地址 + 0 = 写模式 (W) → TRA = 1 (发送模式)
- 地址 + 1 = 读模式 (R) → TRA = 0 (接收模式)

STM32有协议序列机制：

| 操作 | 清除的标志位 |
|------|------------|
| 写DR | SB |
| 读SR1 + 读SR2 | ADDR |
| 读SR1 + 写CR1 | AF |
| 读DR | RXNE |

```text
步骤 3: 清除 ADDR（关键！）
─────────────────────────
你的代码:
    uint32_t tmp;
    tmp = I2C1->SR1;  // 读 SR1
    tmp = I2C1->SR2;  // 读 SR2（硬件自动清除 ADDR）

SR1: ADDR=0 (已清除)
SR2: 无变化，但读取动作触发清除

你的动作: 无，等待数据到来


步骤 4: 接收数据
─────────────────────────
硬件动作: 从机发送数据 → 硬件自动放到 DR

SR1: RXNE=1 (接收缓冲区有数据)
SR2: TRA=0 (接收模式)
DR:  存着收到的数据

你的动作: 检测 SR1.RXNE=1
          → 读 DR 取出数据: data = I2C1->DR;
          → RXNE 自动清除


步骤 5: 发送 Stop
─────────────────────────
你的代码: I2C_GenerateSTOP(I2C1, ENABLE);

SR1: 无变化
SR2: BUSY=0, MSL=0 (总线空闲)
DR:  无变化

通信结束。
```

可以这样来理解：
程序触发操作后，硬件会自动完成操作，然后修改状态位。
