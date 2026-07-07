import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from imagefactory import Template, TextLayer, RectLayer, render, generate_batch


def basic_template():
    return Template(width=400, height=200, background="#123456", layers=[
        TextLayer(text="Hello {name}", x=200, y=100, anchor="mm", size=24,
                  color="white"),
    ])


def test_render_size_and_mode():
    img = render(basic_template(), {"name": "World"})
    assert img.size == (400, 200)
    assert img.mode == "RGBA"


def test_placeholder_missing_key_raises():
    try:
        render(basic_template(), {})
        assert False, "빠진 키는 KeyError가 나야 한다"
    except KeyError:
        pass


def test_gradient_and_rect():
    tpl = Template(width=100, height=100,
                   background=("#000000", "#ffffff"),
                   layers=[RectLayer(x=10, y=10, width=50, height=50,
                                     fill="#ff000080", radius=8)])
    img = render(tpl)
    top = img.getpixel((50, 0))
    bottom = img.getpixel((50, 99))
    assert sum(top[:3]) < sum(bottom[:3])  # 위가 어둡고 아래가 밝다


def test_korean_text_renders():
    tpl = Template(width=300, height=100, background="white", layers=[
        TextLayer(text="안녕하세요", x=150, y=50, anchor="mm", size=30,
                  color="black"),
    ])
    img = render(tpl)
    # 글자가 실제로 찍혔는지: 흰 배경이 아닌 픽셀이 존재해야 한다
    colors = img.convert("L").getcolors(maxcolors=100000)
    assert any(value < 200 for _, value in colors)


def test_wrap_breaks_long_text():
    tpl = Template(width=300, height=200, background="white", layers=[
        TextLayer(text="one two three four five six seven eight",
                  x=10, y=10, size=24, color="black", max_width=150),
    ])
    img = render(tpl)  # 예외 없이 렌더링되면 통과
    assert img.size == (300, 200)


def test_generate_batch(tmp_path):
    rows = [{"name": "a"}, {"name": "b"}]
    paths = generate_batch(basic_template(), rows, str(tmp_path),
                           filename="card_{name}.png")
    assert [os.path.basename(p) for p in paths] == ["card_a.png", "card_b.png"]
    assert all(os.path.exists(p) for p in paths)


def test_generate_batch_jpeg_converts_mode(tmp_path):
    paths = generate_batch(basic_template(), [{"name": "x"}], str(tmp_path),
                           filename="card_{_index}.jpg")
    from PIL import Image
    assert Image.open(paths[0]).mode == "RGB"


def test_template_from_json():
    tpl = Template.from_json("""
    {"width": 120, "height": 80, "background": ["#000000", "#222222"],
     "layers": [{"kind": "text", "text": "{t}", "x": 10, "y": 10,
                 "size": 16, "color": "white"}]}
    """)
    img = render(tpl, {"t": "hi"})
    assert img.size == (120, 80)
