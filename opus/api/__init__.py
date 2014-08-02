import ctypes
from ctypes.util import find_library


libopus = ctypes.CDLL('libopus-0.dll')

c_int_pointer = ctypes.POINTER(ctypes.c_int)
c_int16_pointer = ctypes.POINTER(ctypes.c_int16)
c_float_pointer = ctypes.POINTER(ctypes.c_float)
