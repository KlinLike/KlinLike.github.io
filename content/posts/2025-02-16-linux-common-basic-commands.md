---
title:  "Linux常用基础命令"
date: 2025-02-16T14:56:05+08:00
tags: [linux]
---

# 目录命令
- ls ： 列出目录
- cd ： 切换目录
- pwd ： 显示当前目录（工作目录，print working directory）
- mkdir ： 创建新的目录
- rmdir : 删除空的目录
- cp ：复制文件或目录
- rm ： 移除文件或目录
- mv ： 移动文件或目录，也用于重命名文件或目录

1.   可以使用 man 命令来查看命令的使用文档，如 man cp。
2.   ls -l 可以查看更加详细的文件信息
3.   怎么理解mv即可以移动又可以重命名呢 ？移动命令的本质是更换目录，但是不对文件内容做修改。通过更换目录，不但能实现移动，也能实现重命名（重命名也是更换目录，只是换的是文件名级别）。
4.   出于对性能、安全性等考虑，rmdir只能用于删除空目录，否则会报错。

# 文件常用命令
- cat ： 显示全部文件内容，从第一行开始（因此不适合长文本）
- more ： 逐页面显示文件的内容（适合长文本，按Enter可以翻页）
- head : 查看文本内容的前几行
- tail ： 查看文本内容的最后几行

1. head 和 tail 使用参数 -n 都可以指定查看的行数，如 head -n 10 a.txt 是查看 a.txt 的前10行。

# 电源
- sudo reboot ： 重启
- sudo shutdown : 立即关闭系统（不是标准指令，可能会有未定义行为）
- sudo shutdown -h now ： 立刻关闭系统（ -h 是 halt的缩写）
- sudo shutdown -h +30 ： 30s后关闭系统
- sudo shutdown -r now ： 立刻重启（ -r 是 reboot 的缩写）
- sudo shutdown -r +30 ： 30s后重启
- sudo shutdown -r 09:00 ： 早上９点重启
- sudo shutdown -c ： 取消重启计划 （ -c 是cancel 的缩写）

1. sudo shutdown -h now 中的 -h 之所以是 halt 的缩写，是因为在不同的系统配置中，可能会有不同的行为，比如切断电源或停机。
2. 电源操作关系到系统安全，需要超级用户权限，所以需要添加sudo前缀。

# 权限和用户
- chmod ： 更改文件或目录的权限（change mod 的缩写）
- chown ： 更改文件或目录的所有者和所属组
- useradd 和 userdel ： 增加和删除用户
- groupadd 和 groupdel ： 增加和删除用户组
- passwd ： 设置用户密码

##### 代码示例
```
# 为 a.txt 增加执行权限
chmod +x a.txt
# 为 a.txt 打开所有权限，使用数字模式
chmod 777 a.txt

# 将 a.txt 的所有者改为user，所属组改为group
chown user:group a.txt

# 添加用户 newuser
sudo useradd newuser
# 更改 newuser 的用户密码
sudo passwd newuser
# 删除用户 newuser
sudo userdel newuser

# 添加组 newgroup
sudo groupadd newgroup
# 删除组 newgroup
sudo groupdel newgroup

```

##### 怎么理解chmod的数字模式？
&emsp;&emsp;chmod用数字模式设置权限使用的是三位八进制数，每一位八进制数对应不同的用户类别，从左到右依次是文件所有者（owner）、所属组（group）、其他用户（others）。如 chmod 700 a.txt 是给所有者设置权限7，所属组和其他用户都设置权限0。
&emsp;&emsp;对于每一个权限数字，都可以拆分为3个权限位：执行权限x对应的是数值1，写权限w对应的是数值2，读权限对应的是数值4。因此完整的rwx对应的是数字7（1+2+4）。
&emsp;&emsp;再举例，如只想让文件所有者有完整权限，其余用户只有读写权限，可以执行 chmod 755 a.txt。

##### 什么是用户组
&emsp;&emsp;通过用户组，可以一次性管理组内的多个用户，是一种简化用户管理的机制。如用户a和用户b都属于用户组reader，系统管理员可以只给用户组reader提供特定目录下的read权限，这样用户a和b都只能读取特定文件，而不能修改或执行。

# 进程
- ps ： 查看所有进程的状态
- top ： 动态地显示进程和资源的占用情况（ctrl+c退出）

1. 使用 ps -ef 可以查看更加详细的进程信息：
![ps -ef]({{ site.baseurl }}/assets/images/2025216/ps -ef.png)

2. 如果安装了 htop，可以用更好的界面来查看top指令的信息：
![htop]({{ site.baseurl }}/assets/images/2025216/htop.png)

# 网络
- ping ： 测试网络连通性
- ifconfig 和 ip addr show ： 查看网络接口的信息
- ss ： 查看网络连接和接口状态

![ping]({{ site.baseurl }}/assets/images/2025216/ping.png)

![ifconfig & ip addr show]({{ site.baseurl }}/assets/images/2025216/ifconfig & ip addr show.png)

![ss]({{ site.baseurl }}/assets/images/2025216/ss.png)





