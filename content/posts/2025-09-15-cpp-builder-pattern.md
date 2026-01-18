---
title:  "Cpp函数参数过多如何优化->构建器模式"
date: 2025-09-15T19:30:42+08:00
tags: [C++, 设计模式]
---

# Intro
在开发过程中，我们有时候会遇到一种情况：一个函数确实需要传入很多参数，但一大堆参数看起来很费劲，在屏幕上左右拖动也很恼人。此时引入构建器模式可以缓解这个困境。
构建器模式本质上是链式调用，实现的要点是：让每一个设置属性的函数都返回指向它操作对象的指针。
-> C语言因为没有面向对象特性，实现构建器模式要复杂很多

# Cpp实现
TODO：创建一个 Computer 对象，包含属性：cpu\ram\gpu\storage\screen_size

## 如果不使用构建器模式
```
class Computer {
	public:
	    Computer(const std::string& cpu, int ram, const std::string& storage, const std::string& gpu, double screenSize)
        : m_cpu(cpu), m_ram(ram), m_gpu(gpu), m_storage(storage), m_screen_size(screenSize) {}
    private:
	    std::string m_cpu;
	    int m_ram;
        std::string m_gpu;
        std::string m_storage;
        double m_screen_size;
}

```

# 使用构建器模式
```
class Computer {
public:
	// 嵌套的Builder类
    class Builder {
    public:
        // Builder 的构造函数只接收必需参数
        Builder(std::string cpu, int ram) : m_cpu(cpu), m_ram(ram) {}

        // 每个 setter 方法都返回 Builder& -> 返回 Builder& 比 Builder* 更直观优雅
        Builder& withGpu(std::string gpu) {
            m_gpu = gpu;
            return *this;
        }

        Builder& withStorage(std::string storage) {
            m_storage = storage;
            return *this;
        }

        Builder& withScreenSize(double size) {
            m_screen_size = size;
            return *this;
        }

        // 最终的 build 方法创建并返回一个 Computer 对象
        Computer build() {
            // 在这里可以添加复杂的校验逻辑，确保配置合法
            return Computer(*this);
        }

    private:
        friend class Computer; // 允许 Computer 访问 Builder 的私有成员
        std::string m_cpu;
        int m_ram;
        std::string m_gpu = "Integrated";
        std::string m_storage = "256GB SSD";
        double m_screen_size = 14.0;
    };

private:
    // Computer 的构造函数是私有的 只能通过 Builder 来创建 Computer 对象
    Computer(const Builder& builder)
        : m_cpu(builder.m_cpu),
          m_ram(builder.m_ram),
          m_gpu(builder.m_gpu),
          m_storage(builder.m_storage),
          m_screen_size(builder.m_screen_size) {}

    std::string m_cpu;
    int m_ram;
    std::string m_gpu;
    std::string m_storage;
    double m_screen_size;
};

int main() {
    Computer gamingPC = Computer::Builder("AMD R7", 32)
                            .withStorage("2TB NVMe SSD")
                            .withGpu("NVIDIA RTX 4080")
                            .withScreenSize(17.3)
                            .build();

    // 只指定了 CPU\GPU 的电脑
    Computer devPC = Computer::Builder("Intel i9", 64)
                         .withGpu("NVIDIA RTX 4090")
                         .build();

}
```