---
title:  "对 C++中整型转换问题的一些探讨"
date: 2024-06-30 18:22:00 -0700
tags: [c++, programming]
---

#问题1：直接把int转换为short会发生什么？
  &emsp;&emsp;因为short的取值范围是-32768 到 32767，而int的取值范围远大于此，这就产生了一个问题：如果int内存储的数字超过了short的可表示范围，会发生什么。

	// 你可以把文章的所有代码都copy下来执行看看效果

	#include <iostream>
	#include <limits>
	#include <bitset>

	// 首先使用C风格的强制类型转换看看效果：
    int32_t longValue = 32768;
    int16_t shortValue = (int16_t)longValue;
    std::cout << "C style cast: " << shortValue << std::endl;

  &emsp;&emsp;运行后发现shortValue的值变成了 -32768 ,这和我们的预期大相径庭*（实际上，我希望如果超过了short可表示的最大值，最起码应该设置为short能表示的最大值，即32767）*<br/>
  &emsp;&emsp;那使用推荐的static_cast会有什么区别吗？

	shortValue = static_cast<int16_t>(longValue);
    std::cout << "static cast: " << shortValue << std::endl;

  &emsp;&emsp;不难发现，计算结果和第一种转换方法没什么区别。
  
	尽管计算结果一样，static_cast也是更加推荐的方法。
	我能想到的原因有两个：
	1. 可读性更强（相较于隐式转换）
	2. static_cast在编译的时候会进行严格的类型检查，确保转换是合法的（尽管如此，它也不能应付所有情况）

  &emsp;&emsp;同样的，使用隐式转换也不会有什么区别。但强烈建议避免这类隐式转换，因为会提高代码的维护成本。

	shortValue = longValue;
    std::cout << "implicit: " << shortValue << std::endl;

##1.1 为什么是 -32768 呢？
  &emsp;&emsp;因为32768在32位的二进制表示为 

	0000 0000 0000 0000 1000 0000 0000 0000
  &emsp;&emsp;转换为16位的short后发生了截断，只保留了低16位，也就是

	1000 0000 0000 0000
  &emsp;&emsp;因为有符号整数使用补码表示，而1000 0000 0000 0000 是 -32768 的补码。

##1.2 补码的计算过程
  &emsp;&emsp;*p.s. 这里没看懂也没关系，文章后面有关于原码反码补码的说明，可以看完再返回阅读这段*<br/>
  &emsp;&emsp;先来计算-32767的补码，计算方法是对应正数原码取反再加一

	0111 1111 1111 1111
  &emsp;&emsp;取反得到

	1000 0000 0000 0000
  &emsp;&emsp;加一得到

	1000 0000 0000 0001

  &emsp;&emsp;验证正确性

		0111 1111 1111 1111
	+	1000 0000 0000 0001
	= 1 0000 0000 0000 0000
  &emsp;&emsp;舍去最高位得到 0，验证正确。<br/>
  &emsp;&emsp;那么问题来了，32768的原码是

	0 1000 0000 0000 0000

  &emsp;&emsp;取反后得到

	1 0111 1111 1111 1111
  &emsp;&emsp;加一得到

	1 1000 0000 0000 0000

  &emsp;&emsp;为什么-32768的补码不是 1 1000 0000 0000 0000 呢? <br/>
  &emsp;&emsp;因为16位原码无法表示32768，所以-32768作为边界值，它的补码不是通过取反再加一来计算的，而是直接使用

	1000 0000 0000 0000
  &emsp;&emsp;来表示。即边界值的补码是特殊值。

#问题2：如果是unsigned short转换为int呢？
  &emsp;&emsp;好消息是，如果是unsigned short转换为int，并不需要担心取值问题，因为int可以覆盖unsigned short的所有取值。 <br/> 
  &emsp;&emsp;在这种情况下，可以考虑使用隐式转换。但static_cast仍然是推荐的方法

#问题3：如何安全地将unsigned int转换为short
  &emsp;&emsp;因为unsigned int可表示的数值范围远大于short可表示的数值范围，所以转换前必须确保unsigned int的值在short能表达的范围内，才能进行安全的转换，否则就要考虑使用其他逻辑。<br/>
  &emsp;&emsp;可以采用类似下面的逻辑：

	unsigned int uLongValue = 40000;

    if (uLongValue <= std::numeric_limits<int16_t>::max())
    {
        shortValue = static_cast<int16_t>(uLongValue);
    }
    else
    {
        shortValue = std::numeric_limits<int16_t>::max();
        // or throw an error
    }

***
*下面是拓展问题*
#问题4：为什么int的32678赋值给short，会变成-32768呢？
&emsp;&emsp;要弄明白这个问题，首先要对原码、反码和补码有基本的了解。<br/>
&emsp;&emsp;所谓原码、反码、补码，都是在二进制数据的基础上讨论的：

	1. 原码
		使用最高位（最左边）表示符号（0为正数，1为负数），剩余的位表示数值的绝对值
	2. 反码
		正数和原码相同 -> 实际上三种码的正数表示都相同
		负数的反码是其原码数值位的取反
	3. 补码
		正数的原码和反码相同
		负数的补码是其反码加1

&emsp;&emsp;那这三种表示方法有什么区别呢？<br/>

	1. 原码和反码的表示直接，但是不方便计算机计算，补码的计算则更加高效
		-> 因为补码可以直接通过二进制加法来实现加减法，而且符号位也可以参与运算
	2. 原码和反码存在正负0的问题（0000 0000和1000 0000),补码则没有这个问题
		-> 8bit原码和反码的表示范围都是-127~127,因为有正负零
		-> 而8bit补码的表示范围是 -128~127，只有一个0

&emsp;&emsp;因为补码的优势，C++默认使用补码表示有符号整数。实际上，补码是现代计算机系统中表示有符号整数的标准方法。<br/>
&emsp;&emsp;举个例子，以 8bit数据为例:<br/>

	原码
		0000 0001	+1
		1000 0001	-1 -> 只有符号位不一样
	反码
		0000 0001	+1
		1111 1110	-1 -> 原码反码的转换是不操作符号位的，这是标记正负的重要标识，而且正负的补码有不同的阅读/转换方法
	补码
		0000 0001	+1 -> 三种码的正数表示都是一样的
		1111 1111	-1

&emsp;&emsp;不要以为符号位是一成不变的,实际上在某些情况下,符号位会发生改变。<br/>
&emsp;&emsp;比如对补码表示的 -1 加 1

	11111111 + 00000001 = 00000000 (实际上是100000000，但是最高位被丢弃了)
&emsp;&emsp;但是这个运算结果是正确的，即

	-1 + 1 = 0
&emsp;&emsp;从这个例子也能看出补码是如何通过加法来实现减法的（因为负一加一也能理解为一减一）

    // 下面是输出 -1、0、1 的补码的程序，
	// 你可以修改为任意数字查看对应的补码
    shortValue = -1;
    std::cout << std::bitset<8>(shortValue) << std::endl;
    shortValue = 0;
    std::cout << std::bitset<8>(shortValue) << std::endl;
    shortValue = 1;
    std::cout << std::bitset<8>(shortValue) << std::endl;

#问题5：如果直接把unsigned short 赋值给 int会发生什么
&emsp;&emsp;之所以想到这个问题，是因为工作中遇到错误的类型赋值导致随机的程序卡顿，
那为什么会这样呢？<br/>
&emsp;&emsp;下面是当时的代码的关键部分

    unsigned int uValue = 10; // 某个根据情况生成的值，这里假设是10
    for (unsigned int i = 0; i < (uValue-1); i++)
    {
    do something...
        std::cout << "ver 1: " << i << std::endl;
    }

&emsp;&emsp;似乎一切都很正常，程序也能如预期般执行。<br/>
&emsp;&emsp;但uValue的值，有很低的概率会是0（实际上0是异常情况）。<br/>
&emsp;&emsp;此时uValue的二进制数据是32个0（无符号整型没有符号位），经过uValue - 1后发生了无符号整数溢出，<br/>
导致其二进制数据变成了32个1，即unsigned int能表示的最大值，此时这个循环将会被执行4294967295次。

	文档对溢出的解释：
	Unsigned integer arithmetic is always performed modulo 2^n where n is the number of bits in that particular integer.
	E.g. for unsigned int, adding one to UINT_MAX gives 0, and subtracting one from 0 gives UINT_MAX.

	[原文链接](https://en.cppreference.com/w/cpp/language/operator_arithmetic)

&emsp;&emsp;因此，下面的程序会发生无符号整数溢出。

    uValue = 0;
    std::cout << "unsigned int zero: " << std::bitset<32>(uValue) << std::endl;
    uValue--;
    std::cout << "after unsigned int overflow: " << std::bitset<32>(uValue) << std::endl;
    std::cout << "after unsigned int overflow: " << uValue << std::endl;

    uValue = 0;
    for (unsigned int i = 0; i < (uValue - 1); i++)
    {
    	// do something...
        
        if (i > 10000000)
        {
            std::cout << "ver 2: " << i << std::endl;
            break;
        }
    }

&emsp;&emsp;那么，要如何避免这种错误呢？

	1. 重视生成时的警告信息，如：warning C4018: “<”: 有符号/无符号不匹配
	2. 小心地检查可能发生变量类型转换的代码，使用static_cast显式转换，避免发生隐式转换
	3. 手动检查溢出，如使用<limits>中的std::numeric_limits<type-name>::max()
	4. 使用第三方计算库，如SafeInt
		-> [关于SafeInt](https://learn.microsoft.com/en-us/cpp/safeint/safeint-library?view=msvc-170)