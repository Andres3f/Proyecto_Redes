
def test_img_transfer_fiable_with_loss(tmp_path):
    img_path = tmp_path / 'test3.png'
    make_sample_png(str(img_path), color=(0, 0, 255))
    # run demo (server+client) con pérdida simulada, chunk_size pequeño
    # loss_rate alto para forzar reintentos
    asyncio.run(run_demo(str(img_path), mode='FIABLE', loss_rate=0.4, chunk_size=50))
    recv_path = os.path.join(RECV_DIR, 'test3.png')
    assert os.path.exists(recv_path)
    with open(recv_path, 'rb') as f1, open(img_path, 'rb') as f2:
        assert f1.read() == f2.read()
import asyncio
import os
import tempfile
from PIL import Image
from examples.pruebdemo_img_transfer import run_demo, RECV_DIR


def make_sample_png(path, size=(64, 64), color=(255, 0, 0)):
    img = Image.new('RGB', size, color)
    img.save(path, format='PNG')


def test_img_transfer_fiable(tmp_path):
    img_path = tmp_path / 'test.png'
    make_sample_png(str(img_path))
    # run demo (server+client)
    asyncio.run(run_demo(str(img_path), mode='FIABLE', loss_rate=0.0))
    recv_path = os.path.join(RECV_DIR, 'test.png')
    assert os.path.exists(recv_path)
    with open(recv_path, 'rb') as f1, open(img_path, 'rb') as f2:
        assert f1.read() == f2.read()


def test_img_transfer_semi_fiable(tmp_path):
    img_path = tmp_path / 'test2.png'
    make_sample_png(str(img_path), color=(0, 255, 0))
    # use small chunk_size so image splits in multiple chunks and losses can occur
    asyncio.run(run_demo(str(img_path), mode='SEMI-FIABLE', loss_rate=0.3, chunk_size=50))
    partial_path = os.path.join(RECV_DIR, 'test2.png.partial')
    assert os.path.exists(partial_path)
    # partial file should be non-empty
    assert os.path.getsize(partial_path) > 0
