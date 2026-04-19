---
title: "STM32 HAL库 I2C 三种编程方式：查询、中断与DMA"
date: 2026-04-19T17:31:05+08:00
categories: [系统与性能]
tags: [embedded, i2c, c]
draft: false
---

和串口类似，I2C也有三种方式：

1. 查询方式，阻塞等待，简单直接
2. 中断方式，非阻塞，效率更高
3. DMA方式，适合大数据传输，解放CPU

## HAL库的封装模式

HAL库提供了两种不同的封装模式：普通模式和内存模式。

怎么理解这两种模式的区别呢？用读寄存器举例，可以拆分为两个步骤：

1. 写寄存器地址，也就是告诉从设备要读的地址
2. 读数据

如果我们用普通模式，就需要两次调用，需要先写地址，然后读数据；
如果我们用内存模式，HAL库就帮我们封装了这两步，只需要一次调用就能搞定。

举例：场景为读取 MPU6050 的 WHO_AM_I 寄存器（地址 0x75）。

普通模式：

```c
// ========== 第一步：写寄存器地址 ==========
uint8_t reg_addr = 0x75;
HAL_I2C_Master_Transmit(&hi2c1, 0x68<<1, &reg_addr, 1, 1000);
// 0x68<<1 设备地址左移一位，因为是7bit地址，库会自动处理读写位

// ========== 第二步：读数据 ==========
uint8_t value;
HAL_I2C_Master_Receive(&hi2c1, 0x68<<1, &value, 1, 1000);

// 现在 value = 0x68（WHO_AM_I 返回值）
```

内存模式：

```c
// ========== 一步搞定 ==========
uint8_t value;
HAL_I2C_Mem_Read(&hi2c1, 0x68<<1, 0x75, I2C_MEMADD_SIZE_8BIT, &value, 1, 1000);
// 按照寄存器地址宽度选择 I2C_MEMADD_SIZE_8BIT/I2C_MEMADD_SIZE_16BIT

// 现在 value = 0x68（WHO_AM_I 返回值）
```

但是调用次数的区别只存在于读模式，写模式都是一次，区别只有参数组织方式：

```c
// 写寄存器（普通模式）
uint8_t data[2] = {0x6B, 0x00};  // 寄存器地址 + 数据
HAL_I2C_Master_Transmit(&hi2c1, 0x68<<1, data, 2, 1000);

// 写寄存器（内存模式）
uint8_t value = 0x00;
HAL_I2C_Mem_Write(&hi2c1, 0x68<<1, 0x6B, I2C_MEMADD_SIZE_8BIT, &value, 1, 1000);
```

一般推荐使用内存模式，更方便，除非需要更加细致的控制。

一个有趣的小问题是，为什么普通模式不需要 `I2C_MEMADD_SIZE_8BIT` 这样的参数呢？
核心区别是：HAL库知不知道这是寄存器地址。

在普通模式下，HAL库只管发送这些字节，不关心内容是什么。
而在内存模式下，HAL库知道第一个是寄存器地址，后面的是数据，所以需要关心地址长度。
因为不管是读还是写，第一步都是需要写地址，也就是需要知道地址长度的，所以读写都有这个参数。

封装方式这一节，提到的所有代码调用方式都是查询方式，到这里其实你也掌握了查询方式的用法了，其实非常简单。

[相关代码改动（查询方式实现）](https://github.com/KlinLike/hal-driver-study/commit/3df38ab)

## 中断方式

和其他HAL库函数一样，中断方式的函数带有 `_IT` 后缀，触发中断后立即返回，在回调函数里通知。

| 查询函数 | 中断函数 |
|----------|----------|
| `HAL_I2C_Master_Transmit` | `HAL_I2C_Master_Transmit_IT` |
| `HAL_I2C_Master_Receive` | `HAL_I2C_Master_Receive_IT` |
| `HAL_I2C_Mem_Read` | `HAL_I2C_Mem_Read_IT` |
| `HAL_I2C_Mem_Write` | `HAL_I2C_Mem_Write_IT` |

### 回调

中断方式涉及的回调函数稍微多了一些：

| 回调函数 | 触发条件 |
|----------|----------|
| `HAL_I2C_MasterTxCpltCallback` | Master 发送完成 |
| `HAL_I2C_MasterRxCpltCallback` | Master 接收完成 |
| `HAL_I2C_MemTxCpltCallback` | Mem 发送完成 |
| `HAL_I2C_MemRxCpltCallback` | Mem 接收完成 |
| `HAL_I2C_SlaveTxCpltCallback` | Slave 发送完成 |
| `HAL_I2C_SlaveRxCpltCallback` | Slave 接收完成 |
| `HAL_I2C_ErrorCallback` | 任何错误 |
| `HAL_I2C_AbortCpltCallback` | 中止完成 |

按照操作类型分类：

| 类型 | 发送回调 | 接收回调 |
|------|----------|----------|
| Master 普通模式 | `MasterTxCpltCallback` | `MasterRxCpltCallback` |
| Mem 内存模式 | `MemTxCpltCallback` | `MemRxCpltCallback` |
| Slave 从机模式 | `SlaveTxCpltCallback` | `SlaveRxCpltCallback` |

按事件类型分：

| 事件 | 回调函数 |
|------|----------|
| 正常完成 | `xxxCpltCallback` |
| 出错 | `HAL_I2C_ErrorCallback` |
| 中止 | `HAL_I2C_AbortCpltCallback` |

中止回调就是发送了Stop信号后调用的回调，通信出错或者用户中止都会被调用。

### 触发

- `HAL_I2C_Master_Transmit_IT` 普通模式主机发送
- `HAL_I2C_Master_Receive_IT` 普通模式主机接收
- `HAL_I2C_Mem_Write_IT` 内存模式写
- `HAL_I2C_Mem_Read_IT` 内存模式读
- `HAL_I2C_Master_Abort_IT` 终止传输 -> 只有Master可以中止

| 触发函数 | 对应回调 |
|----------|----------|
| `HAL_I2C_Master_Transmit_IT` | `HAL_I2C_MasterTxCpltCallback` |
| `HAL_I2C_Master_Receive_IT` | `HAL_I2C_MasterRxCpltCallback` |
| `HAL_I2C_Mem_Write_IT` | `HAL_I2C_MemTxCpltCallback` |
| `HAL_I2C_Mem_Read_IT` | `HAL_I2C_MemRxCpltCallback` |
| `HAL_I2C_Master_Abort_IT` | `HAL_I2C_AbortCpltCallback` |
| 任何传输出错 | `HAL_I2C_ErrorCallback` |

使用模式：

```text
┌─────────────────────────────────────────────┐
│  程序员逻辑                                  │
├─────────────────────────────────────────────┤
│                                             │
│  1. 调用触发函数                             │
│     HAL_I2C_Mem_Read_IT(...)                │
│         ↓                                   │
│  2. 立即返回，后台传输                        │
│         ↓                                   │
│  3. [程序员自己决定等待方式]                  │
│     while(flag == 0);                       │
│     或做其他事情                             │
│         ↓                                   │
│  4. HAL 调用回调函数                         │
│     HAL_I2C_MemRxCpltCallback()             │
│         ↓                                   │
│  5. [程序员在回调里写逻辑]                    │
│     flag = 1;                               │
│                                             │
└─────────────────────────────────────────────┘
```

[相关代码改动（中断方式实现）](https://github.com/KlinLike/hal-driver-study/commit/ba80b7d)

## DMA

I2C DMA直接跳过，因为这不常用。

原因：

1. I2C传感器通常只读写几个字节，DMA优势不明显
2. I2C有 Start/Stop/ACK/NACK，DMA处理不直观
3. DMA需要处理最后一个字节前禁止ACK等特殊情况，比较麻烦
4. 对大多数I2C应用，中断模式已经够用
