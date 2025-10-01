from time import sleep
from typing import Callable, TypeVar, Generic, List, Set, Optional, Dict, Any, Tuple, Type
from typing_extensions import ParamSpec
from threading import Lock, Thread, Condition
from dataclasses import field
# Define a ParamSpec for the arguments and a TypeVar for the return type
P = ParamSpec('P')
R = TypeVar('R')

class Signal(Generic[P, R]):
	def __init__(self):
		self._listeners: Dict[Optional[str], Tuple[Callable[P, R], bool]] = {}
		self.lock = Lock()

	def connect(self, listener: Callable[P, R], key: Optional[str] = None, auto_disconnect:bool=False) -> None:
		with self.lock:
			if key is None:
				key = listener
			self._listeners[key] = (listener, auto_disconnect)

	def disconnect(self, listener: Callable[P, R], key: Optional[str] = None) -> None:
		with self.lock:
			if key is None:
				key = listener
			if key in self._listeners:
				del self._listeners[key]

	def _call(self, listeners: Dict[Optional[str], Tuple[Callable[P, R], bool]], *args: P.args, **kwargs: P.kwargs) -> Dict[str, R]:
		results: Dict[str, R] = {}
		for key, listener in listeners.items():
			try:
				r = listener[0](*args, **kwargs)
				if isinstance(key, str):
					results[key] = r
			except Exception as e:
				if listener[1]:
					self.disconnect(listener[0], key)
				else:
					raise e
				
		return results
	
	def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dict[str, R]:
		with self.lock:
			listeners = dict(self._listeners)
		return self._call(listeners, *args, **kwargs)
	
	def __deepcopy__(self, memo):
		return self
	
	@classmethod
	def field(cls, compare=False, repr=False, hash=False, init=False, kw_only=True) -> field:
		return field(default_factory=cls, compare=compare, repr=repr, hash=hash, init=init, kw_only=kw_only)

if __name__ == "__main__":
	# Example usage with different listener signatures
	def listener1(x: int, y: str) -> float:
		return len(y) * x
	
	def listener1_2(x: int, y: str) -> float:
		return len(y) * x * 5

	def listener2(x: int) -> int:
		return x * 2

	def listener3() -> str:
		return "No arguments"

	# Create signal instances with different signatures
	signal1 = Signal[[int, str], float]()
	signal2 = Signal[[int], int]()
	signal3 = Signal[[], str]()

	# Connect listeners
	signal1.connect(listener1, "bla")
	signal1.connect(listener1, "listener1")
	signal1.connect(listener1_2, "listener1_2")
	
	signal2.connect(listener2, "listener2")
	signal3.connect(listener3, "listener3")

	# Call the signals
	result1 = signal1(5, "hello")
	result2 = signal2(10)
	result3 = signal3()

	print("Result 1:", signal1(5, "hello"))
	signal1.disconnect("bla")
	
	print("Result 1 (post remove):", signal1(5, "hello"))
	signal1.connect(listener1)
	
	print("Result 1 (post re-add):", signal1(5, "hello"))
	
	print("Result 2:", signal2(10))
	print("Result 3:", signal3())
