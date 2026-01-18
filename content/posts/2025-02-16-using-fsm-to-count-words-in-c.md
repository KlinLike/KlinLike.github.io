---
title:  "🌳使用有限状态机计算文本中英语单词的数量（C语言）"
date: 2025-02-16T22:07:42+08:00
tags: [c, algorithm, fsm, state-machine]
---

# 相关知识点
### 1. 什么是状态机
&emsp;&emsp;状态机由一组状态、转换和事件组成。状态机的基本思想是：系统在任何时刻都处于某一个状态，当某个事件发生时，系统会根据当前状态和事件来决定下一个状态。

### 2. 什么是有限状态机
&emsp;&emsp;有限状态机是状态机的一种特殊形式，它的特点是：
&emsp;&emsp; 1. 状态的数量是有限的
&emsp;&emsp; 2. 转换是基于输入事件触发的
&emsp;&emsp; 3. 每次只能处于一个状态

### 3. main函数的参数
&emsp;&emsp;mian函数可以有两个参数，argc和argv，这两个参数主要用于从命令行向程序传递参数。
```
int main( int argc, char* argv[]);
int main(int argc, char** argv); // 两个声明是等价的
```
&emsp;&emsp;其中 argc 是 argument count，也就是参数的数量。需要注意的是，参数的数量包含程序本身的名称，也就是说至少会有1个参数。
&emsp;&emsp;argv 是 argument vector，是参数数组。数组中每个元素都是一个指向以 '\0' 结尾的字符串的指针，这些字符串就是命令行参数。
&emsp;&emsp;为什么两个声明是等价的呢？是因为数组作为函数参数被传递时，会退化为指向数组首元素的指针，所以char* argv[] 会退化为 char** argv。

### 4. fopen函数
&emsp;&emsp;fopen函数打开一个文件，并返回一个 FILE* 类型的指针，如果打开失败，则会返回NULL。

### 5. fgetc函数
&emsp;&emsp;fgetc从一个文件中读取一个字符，返回读取到的char变量。当读取到文件末尾时，会返回EOF。
&emsp;&emsp;EOF（End Of File），是一个特殊的标识符，代表文件内容的结束位置，在C或C++里EOF通常被定义为-1，这是因为正常情况下getchar或fgetc会返回一个int类型的非负值，用负值可以方便地表示特殊状态。

# 实现思路
&emsp;&emsp;逐个字符地遍历文本文件，并且区分分隔符和单词的组成字符，当上一个字符是分隔符而当下的字符是单词组成字符时（也就是状态从“单词外”变成了“单词内”），计数器加一，就这样一直遍历到文本末尾，就统计出了单词数量。
&emsp;&emsp;状态机记录两种状态：当前处于单词内、当前处于单词外。当事件“遍历到了属于单词内的字符”发生时，检查当前的状态，如果是“当前处于单词外”状态，就进行状态的转换。

# 实现
```
#include <stdio.h>

#define OUT 0
#define IN  1

#define INIT    OUT

// 判断一个字母是不是分隔符，是就返回1，否则返回0
int isSeparator(char c){
    if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
        (c == '\n') || (c == '-')){ // 连字符和换行符需要特殊处理
        return 0;
    } else {
        return 1;
    }
}

// 计算传入文件中的单词数量
int count_word(char* filename){
    int status = INIT;
    int word = 0;   // 已统计到的单词数量

    FILE* fp = fopen(filename, "r");
    if (fp == NULL) {
        return -1;
    }
    
    char c;
    while ((c = fgetc(fp)) != EOF) {
        if (isSeparator(c)) {
            status = OUT;
        } else if (OUT == status) {
            // 状态从 OUT 变成了 IN，代表进入了一个新单词
            status = IN;
            word++;
        } 
    }

    return word;
}

// 通过命令行编译后运行，传入文本文件的文件名作为参数
int main(int argc, char** argv){
    if (argc < 2) {
        return -1;
    }
    printf("word count: %d\n", count_word(argv[1]));
}
```
