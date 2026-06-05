# from __future__ import annotations
# 让当前文件里的类型注解延迟解析。也就是说，Python 不会在定义函数、类的时候立刻去计算类型注解，而是先把它们保存起来，等真正需要时再解析。
class User:
    def get_friend(self) -> "User":
        return User()