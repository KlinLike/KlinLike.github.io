---
title: "RTOS临界区保护：从原子操作到Mutex的选择"
date: 2026-03-28T10:00:40+08:00
categories: [并发]
tags: [embedded, concurrency, mutex, atomic]
draft: false
---

## 重要

最好的方法是通过架构设计消除冲突，比如把多任务共同读写改为单任务写，多任务读，锁是最后的手段。

## 原子操作 - 最轻的保护措施，适合单个标志位

```c
volatile int status;  // volatile 防止编译器优化掉读取
```

单核MCU上，对一个对齐的 int/u8 的读写本身就是原子的（一条指令完成）。volatile 确保每次都从内存读取，不被缓存到寄存器。

局限：只能保护单个变量，不能保护复合操作比如先读后写。

## 关中断 - 很轻，适合极短的临界区

```c
u32 irq = local_irq_save();    // 关中断，保存之前的状态
g_timers[i].status = TIMER_EMPTY;
g_timers[i].endTimestamp = 0;
local_irq_restore(irq);        // 恢复中断
```

关中断期间RTOS调度器无法切换任务（因为调度器靠中断驱动），相当于临时获得了独占CPU的权限。

关键是要快，关中断的时间不能超过几微秒，否则会影响中断响应延迟。

## Mutex/信号量 - 较重，适合长临界区

```c
os_mutex_pend(&timer_mutex, 0);   // 获取锁（可能导致任务挂起等待）
timerEnsureAlloc();
g_timers[i].endTimestamp = getTimeStamp() + totalSeconds;
g_timers[i].totalSeconds = totalSeconds;
g_timers[i].status = TIMER_RUNNING;
os_mutex_post(&timer_mutex);      // 释放锁
```

如果锁被占用，等待方的任务会挂起，让出CPU。
