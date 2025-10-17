import pytest
import random
from src.transporte.fragmentation import pack_chunk, unpack_chunk, Reassembler


def fragment_bytes(data: bytes, chunk_size: int):
    chunks = []
    total_len = len(data)
    total_chunks = (total_len + chunk_size - 1) // chunk_size
    for i in range(total_chunks):
        offset = i * chunk_size
        part = data[offset:offset + chunk_size]
        pkt = pack_chunk(part, total_len, offset, i, total_chunks, compressed=False)
        chunks.append(pkt)
    return chunks


def test_pack_unpack_roundtrip():
    data = b'abcdefgh' * 100
    chunks = fragment_bytes(data, 128)
    # unpack and assemble via Reassembler
    meta0, payload0 = unpack_chunk(chunks[0])
    r = Reassembler(meta0['total_len'], meta0['total_chunks'], timeout=1.0)
    for pkt in chunks:
        meta, payload = unpack_chunk(pkt)
        r.add_chunk(meta['chunk_id'], meta['offset'], payload)
    assembled = r.assemble()
    assert assembled == data


def test_reassembler_with_loss():
    data = b'0123456789' * 1000
    chunks = fragment_bytes(data, 256)
    # drop random 10% of chunks
    keep = []
    for c in chunks:
        if random.random() > 0.1:
            keep.append(c)
    meta0, _ = unpack_chunk(keep[0])
    r = Reassembler(meta0['total_len'], meta0['total_chunks'], timeout=0.5)
    for pkt in keep:
        meta, payload = unpack_chunk(pkt)
        r.add_chunk(meta['chunk_id'], meta['offset'], payload)
    if r.is_complete():
        assert r.assemble() == data
    else:
        assert not r.is_complete()


def test_reassembler_out_of_order():
    data = b'XYZ' * 1000
    chunks = fragment_bytes(data, 500)
    random.shuffle(chunks)
    meta0, _ = unpack_chunk(chunks[0])
    r = Reassembler(meta0['total_len'], meta0['total_chunks'], timeout=1.0)
    for pkt in chunks:
        meta, payload = unpack_chunk(pkt)
        r.add_chunk(meta['chunk_id'], meta['offset'], payload)
    assert r.is_complete()
    assert r.assemble() == data
