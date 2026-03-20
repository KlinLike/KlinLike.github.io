---
title: "STM32F103的GPIO中断涉及哪些寄存器"
date: 2026-03-20T16:49:54+08:00
categories: [系统与性能]
tags: [embedded, kernel]
draft: false
---

## 1. GPIO与路由配置

先告诉芯片需要用哪个引脚：

`GPIOx_CRL` / `GPIOx_CRH` 配置引脚模式：MODE 置 00（输入），CNF 置 10（上拉/下拉输入），再由 `GPIOx_ODR` 对应位选择上拉（1）或下拉（0）

`AFIO_EXTICR` 设置把引脚接通到EXTI中断线上，比如可以配置 `PA0`/`PB0`.../`PG0` 其中的一个接通到 EXTI0 中断线上。

## 2. EXTI 外部中断模块

EXTI中有几个寄存器负责捕捉信号和放行：

`EXTI_RTSR` (Rising Trigger Selection) 上升沿触发选择

`EXTI_FTSR` (Falling Trigger Selection) 下降沿触发选择

`EXTI_IMR` (Interrupt Mask) 中断屏蔽寄存器：写入1开放中断，写入0屏蔽中断。

`EXTI_PR` (Pending Register) 挂起寄存器：当中断发生时，硬件会将对应的位设为1。需要注意手动清理这个寄存器，否则CPU会反复进中断。

## 3. NVIC 中断管家

至此，信号就来到了内核层，NVIC负责统一调度。

`NVIC_ISER` (Interrupt Set-Enable Register) 中断设置使能：每个中断通道如 `EXTI0_IRQn` 在寄存器里占1位

`NVIC_IP` (Interrupt Priority Registers) 优先级寄存器

`NVIC_ICPR` (Interrupt Clear-Pending Register) 清除NVIC层的挂起标志：通常硬件自动处理，但也支持手动操作。

## 4. CPU全局控制

CPU内核内部有一个 `PRIMASK` 全局中断屏蔽寄存器，当它被置1时，除了硬复位和不可屏蔽中断，其他所有中断都会被屏蔽。
