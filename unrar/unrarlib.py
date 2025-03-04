# -*- coding: utf-8 -*-

# Copyright (C) 2012  Matias Bordese
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ctypes
import os
import platform

from ctypes.util import find_library
from packaging import version

from unrar import constants


__all__ = ["RAROpenArchiveDataEx", "RARHeaderDataEx", "RAROpenArchiveEx",
           "RARCloseArchive", "RARReadHeaderEx", "RARProcessFile",
           "RARSetPassword", "RARGetDllVersion", "RARSetCallback",
           "dostime_to_timetuple"]


CURR_PATH = os.path.abspath(os.path.dirname(__file__))
lib_path = os.environ.get('UNRAR_LIB_PATH', None)

# find and load unrar library
unrarlib = None
if platform.system() == 'Windows':
    from ctypes.wintypes import HANDLE as WIN_HANDLE
    HANDLE = WIN_HANDLE
    UNRARCALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint,
                                       ctypes.c_long, ctypes.c_long,
                                       ctypes.c_long)
    bundled_path = os.path.join(CURR_PATH, 'libunrar.dll')
    lib_path = lib_path or find_library("unrar.dll")
    if lib_path:
        unrarlib = ctypes.WinDLL(lib_path)
    elif os.path.exists(bundled_path):
        unrarlib = ctypes.WinDLL(bundled_path)
else:
    # assume unix
    HANDLE = ctypes.c_void_p
    UNRARCALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint,
                                     ctypes.c_long, ctypes.c_long,
                                     ctypes.c_long)
    if platform.system() == "Darwin":
        bundled_path = os.path.join(CURR_PATH, 'libunrar.dylib')
    else:
        bundled_path = os.path.join(CURR_PATH, 'libunrar.so')

    lib_path = lib_path or find_library("unrar")
    if lib_path:
        unrarlib = ctypes.cdll.LoadLibrary(lib_path)
    elif os.path.exists(bundled_path):
        unrarlib = ctypes.cdll.LoadLibrary(bundled_path)
    elif platform.system() == "Darwin":
        # maybe this is MacOS, check if library is installed by Homebrew.
        # expected installed dir and lib filename
        BREW_UNRAR_PATH = "/usr/local/Cellar/unrar/"
        LIB_FILENAME = "libunrar.dylib"

        if os.path.isdir(BREW_UNRAR_PATH):
            # find latest available version
            latest_version = max(
                version.parse(v) for v in os.listdir(BREW_UNRAR_PATH))
            lib_path = "{}{}/lib/{}".format(
                BREW_UNRAR_PATH, latest_version, LIB_FILENAME)
            unrarlib = ctypes.cdll.LoadLibrary(lib_path)
        else:
            raise LookupError(
                "Couldn't locate libunrar.dylib. "
                "Install it using Homebrew (https://brew.sh/), "
                "or build it yourself (https://www.rarlab.com/rar_add.htm)."
            )


if unrarlib is None:
    raise LookupError("Couldn't find path to unrar library.")


def dostime_to_timetuple(dostime):
    """Convert a RAR archive member DOS time to a Python time tuple."""
    dostime = dostime >> 16
    dostime = dostime & 0xffff
    day = dostime & 0x1f
    month = (dostime >> 5) & 0xf
    year = 1980 + (dostime >> 9)
    second = 2 * (dostime & 0x1f)
    minute = (dostime >> 5) & 0x3f
    hour = dostime >> 11
    return (year, month, day, hour, minute, second)


class UnrarException(Exception):
    """Lib errors exception."""

class ArchiveEnd(UnrarException):
    """End of Archive event - code 10"""

class NoMemoryError(UnrarException):
    """No memory error - code 11"""

class BadDataError(UnrarException):
    """Bad data error - code 12"""

class BadArchiveError(UnrarException):
    """Bad archive error - code 13"""

class UnknownFormatError(UnrarException):
    """Unknown format error - code 14"""

class OpenError(UnrarException):
    """Open error - code 15"""

class CreateError(UnrarException):
    """Create error - code 16"""

class CloseError(UnrarException):
    """Close error - code 17"""

class ReadError(UnrarException):
    """Read error - code 18"""

class WriteError(UnrarException):
    """Write error - code 19"""

class SmallBufError(UnrarException):
    """Buffer too small error - code 20"""

class UnknownError(UnrarException):
    """Unknown error - code 21"""

class MissingPassword(UnrarException):
    """Missing password - code 22"""

#ReferenceError is a built-in
class RarReferenceError(UnrarException):
    """Reference error - code 23"""

class BadPassword(UnrarException):
    """Bad password - code 24"""


class _Structure(ctypes.Structure):
    """Customized ctypes Structure base class."""

    def __repr__(self):
        """Print the structure fields."""
        res = []
        for field in self._fields_:
            field_value = repr(getattr(self, field[0]))
            res.append('%s=%s' % (field[0], field_value))
        return self.__class__.__name__ + '(' + ','.join(res) + ')'


class RAROpenArchiveDataEx(_Structure):
    """Rar compressed file structure."""
    _fields_ = [
        ('ArcName', ctypes.c_char_p),
        ('ArcNameW', ctypes.c_wchar_p),
        ('OpenMode', ctypes.c_uint),
        ('OpenResult', ctypes.c_uint),
        ('_CmtBuf', ctypes.c_void_p),
        ('CmtBufSize', ctypes.c_uint),
        ('CmtSize', ctypes.c_uint),
        ('CmtState', ctypes.c_uint),
        ('Flags', ctypes.c_uint),
        ('Reserved', ctypes.c_uint * 32),
    ]

    def __init__(self, filename, mode=constants.RAR_OM_LIST):
        # comments buffer, max 64kb
        self.CmtBuf = ctypes.create_string_buffer(b'', 64 * 1024)
        super(RAROpenArchiveDataEx, self).__init__(
            ArcName=None,
            ArcNameW=filename, OpenMode=mode,
            _CmtBuf=ctypes.addressof(self.CmtBuf),
            CmtBufSize=ctypes.sizeof(self.CmtBuf))

    def __str__(self):
        return self.ArcNameW


class RARHeaderDataEx(_Structure):
    """Rar file header structure."""
    _fields_ = [
        ('ArcName', ctypes.c_char * 1024),
        ('ArcNameW', ctypes.c_wchar * 1024),
        ('FileName', ctypes.c_char * 1024),
        ('FileNameW', ctypes.c_wchar * 1024),
        ('Flags', ctypes.c_uint),
        ('PackSize', ctypes.c_uint),
        ('PackSizeHigh', ctypes.c_uint),
        ('UnpSize', ctypes.c_uint),
        ('UnpSizeHigh', ctypes.c_uint),
        ('HostOS', ctypes.c_uint),
        ('FileCRC', ctypes.c_uint),
        ('FileTime', ctypes.c_uint),
        ('UnpVer', ctypes.c_uint),
        ('Method', ctypes.c_uint),
        ('FileAttr', ctypes.c_uint),
        ('_CmtBuf', ctypes.c_void_p),
        ('CmtBufSize', ctypes.c_uint),
        ('CmtSize', ctypes.c_uint),
        ('CmtState', ctypes.c_uint),
        ('Reserved', ctypes.c_uint * 1024),
    ]

    def __init__(self):
        # comments buffer, max 64kb
        self.CmtBuf = ctypes.create_string_buffer(b'', 64 * 1024)
        super(RARHeaderDataEx, self).__init__(
            _CmtBuf=ctypes.addressof(self.CmtBuf),
            CmtBufSize=ctypes.sizeof(self.CmtBuf))

    def __str__(self):
        return self.FileNameW


def _c_func(func, restype, argtypes, errcheck=None):
    """Wrap c function setting prototype."""
    func.restype = restype
    func.argtypes = argtypes
    if errcheck is not None:
        func.errcheck = errcheck
    return func


def _check_open_result(res, func, args):
    if res is None:
        raise UnrarException("Archive open error")
    # res is the archive handle
    return res


def _check_readheader_result(res, func, args):
    if res == constants.SUCCESS:
        return res
    elif res == constants.ERAR_END_ARCHIVE: #10
        raise ArchiveEnd()
    elif res == constants.ERAR_NO_MEMORY: #11
        raise NoMemoryError("Not enough memory")
    elif res == constants.ERAR_BAD_DATA: #12
        raise BadDataError("Bad header data.")
    elif res == constants.ERAR_BAD_ARCHIVE: #13
        raise BadArchiveError("Not valid RAR archive")
    elif res == constants.ERAR_UNKNOWN_FORMAT: #14
        raise UnknownFormatError("Unknown archive format")
    elif res == constants.ERAR_EOPEN: #15
        raise OpenError("Volume open error")
    elif res == constants.ERAR_ECREATE: #16
        raise CreateError("File create error")
    elif res == constants.ERAR_ECLOSE: #17
        raise CloseError("File close error")
    elif res == constants.ERAR_EREAD: #18
        raise ReadError("Read error")
    elif res == constants.ERAR_EWRITE: #19
        raise WriteError("Write error")
    elif res == constants.ERAR_SMALL_BUF: #20
        raise SmallBufError("Buffer too small")
    elif res == constants.ERAR_UNKNOWN: #21
        raise UnknownError("Unknown error")
    elif res == constants.ERAR_MISSING_PASSWORD: #22
        raise MissingPassword("Password missing")
    elif res == constants.ERAR_EREFERENCE: #23
        raise RarReferenceError("Reference Error")
    elif res == constants.ERAR_BAD_PASSWORD: #24
        raise BadPassword("Bad password")
    else:
        raise UnrarException("Unknown Error")


def _check_process_result(res, func, args):
    if res == constants.SUCCESS:
        return res
    elif res == constants.ERAR_END_ARCHIVE: #10
        raise ArchiveEnd()
    elif res == constants.ERAR_NO_MEMORY: #11
        raise NoMemoryError("Not enough memory")
    elif res == constants.ERAR_BAD_DATA: #12
        raise BadDataError("File CRC error")
    elif res == constants.ERAR_BAD_ARCHIVE: #13
        raise BadArchive("Not valid RAR archive")
    elif res == constants.ERAR_UNKNOWN_FORMAT: #14
        raise UnknownFormat("Unknown archive format")
    elif res == constants.ERAR_EOPEN: #15
        raise OpenError("Volume open error")
    elif res == constants.ERAR_ECREATE: #16
        raise CreateError("File create error")
    elif res == constants.ERAR_ECLOSE: #17
        raise CloseError("File close error")
    elif res == constants.ERAR_EREAD: #18
        raise ReadError("Read error")
    elif res == constants.ERAR_EWRITE: #19
        raise WriteError("Write error")
    elif res == constants.ERAR_SMALL_BUF: #20
        raise SmallBufError("Buffer too small")
    elif res == constants.ERAR_UNKNOWN: #21
        raise UnknownError("Unknown Error")
    elif res == constants.ERAR_MISSING_PASSWORD: #22
        raise MissingPassword("Missing password")
    elif res == constants.ERAR_EREFERENCE: #23
        raise RarReferenceError("Reference Error")
    elif res == constants.ERAR_BAD_PASSWORD: #24
        raise BadPassword("Bad Password")
    else:
        raise UnrarException("Unknown Error")

def _check_close_result(res, func, args):
    if res == constants.ERAR_ECLOSE:
        raise CloseError("Archive close error")
    # res == SUCCESS
    return res


# Return library API version.
RARGetDllVersion = _c_func(unrarlib.RARGetDllVersion, ctypes.c_int, [])


# Open RAR archive and allocate memory structures (unicode)
RAROpenArchiveEx = _c_func(unrarlib.RAROpenArchiveEx, HANDLE,
                           [ctypes.POINTER(RAROpenArchiveDataEx)],
                           _check_open_result)


# Set a password to decrypt files.
RARSetPassword = _c_func(unrarlib.RARSetPassword, ctypes.c_int,
                         [HANDLE, ctypes.c_char_p])


# Read header of file in archive (unicode).
RARReadHeaderEx = _c_func(unrarlib.RARReadHeaderEx, ctypes.c_int,
                          [HANDLE, ctypes.POINTER(RARHeaderDataEx)],
                          _check_readheader_result)


# Performs action and moves the current position in the archive to
# the next file. Extract or test the current file from the archive
# opened in RAR_OM_EXTRACT mode. If the mode RAR_OM_LIST is set,
# then a call to this function will simply skip the archive position
# to the next file.
RARProcessFile = _c_func(unrarlib.RARProcessFile, ctypes.c_int,
                         [HANDLE, ctypes.c_int, ctypes.c_char_p,
                          ctypes.c_char_p], _check_process_result)


# Performs action and moves the current position in the archive to
# the next file. Extract or test the current file from the archive
# opened in RAR_OM_EXTRACT mode. If the mode RAR_OM_LIST is set,
# then a call to this function will simply skip the archive position
# to the next file. (unicode version)
RARProcessFileW = _c_func(unrarlib.RARProcessFileW, ctypes.c_int,
                          [HANDLE, ctypes.c_int, ctypes.c_wchar_p,
                           ctypes.c_wchar_p], _check_process_result)


# Close RAR archive and release allocated memory. It must be called when
# archive processing is finished, even if the archive processing was stopped
# due to an error.
RARCloseArchive = _c_func(unrarlib.RARCloseArchive, ctypes.c_int, [HANDLE],
                          _check_close_result)


# Set a user-defined callback function to process Unrar events.
RARSetCallback = _c_func(unrarlib.RARSetCallback, None,
                         [HANDLE, UNRARCALLBACK, ctypes.c_long])
