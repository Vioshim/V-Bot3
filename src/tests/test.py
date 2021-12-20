from abc import ABCMeta, abstractmethod


class Cls(metaclass=ABCMeta):
    data: int = 0

    @abstractmethod
    def foo(self) -> None:
        print(self.data)


class Item(Cls):
    def foo(self) -> None:
        super(Item, self).foo()
        print(self.data + 1)


setattr(Item, "foo", 2)

print(Item().foo)


