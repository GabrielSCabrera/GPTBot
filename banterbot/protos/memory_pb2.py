# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: memory.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0cmemory.proto\x12\x04\x63hat"6\n\x07Message\x12\x0c\n\x04role\x18\x01 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x02 \x01(\t\x12\x0c\n\x04name\x18\x03 \x01(\t"}\n\x06Memory\x12\x10\n\x08keywords\x18\x01 \x03(\t\x12\x0f\n\x07summary\x18\x02 \x01(\t\x12\x0e\n\x06impact\x18\x03 \x01(\x03\x12\x11\n\ttimestamp\x18\x04 \x01(\x03\x12\x1f\n\x08messages\x18\x05 \x03(\x0b\x32\r.chat.Message\x12\x0c\n\x04uuid\x18\x06 \x01(\t"9\n\x10MemoryIndexEntry\x12\x0f\n\x07keyword\x18\x01 \x01(\t\x12\x14\n\x0cmemory_uuids\x18\x02 \x03(\t"6\n\x0bMemoryIndex\x12\'\n\x07\x65ntries\x18\x01 \x03(\x0b\x32\x16.chat.MemoryIndexEntryb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "memory_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

    DESCRIPTOR._options = None
    _globals["_MESSAGE"]._serialized_start = 22
    _globals["_MESSAGE"]._serialized_end = 76
    _globals["_MEMORY"]._serialized_start = 78
    _globals["_MEMORY"]._serialized_end = 203
    _globals["_MEMORYINDEXENTRY"]._serialized_start = 205
    _globals["_MEMORYINDEXENTRY"]._serialized_end = 262
    _globals["_MEMORYINDEX"]._serialized_start = 264
    _globals["_MEMORYINDEX"]._serialized_end = 318
# @@protoc_insertion_point(module_scope)
