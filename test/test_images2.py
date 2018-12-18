"""
test_images2.py tests libqtile.images.Img for rendering quality
by comparing known good and bad images to images rendered using
Img().

Image similarity / distance is calculated using imagemagick's convert
utility.
"""
import pytest
import libqtile.images as images
import cairocffi
import subprocess as sp
from collections import namedtuple
from os import path
from glob import glob

def get_imagemagick_version():
    "Get the installed imagemagick version from the convert utility"
    p = sp.Popen(['convert', '-version'], stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = p.communicate()
    lines = stdout.decode().splitlines()
    ver_line = [x for x in lines if x.startswith('Version:')]
    assert len(ver_line) == 1
    version = ver_line[0].split()[2]
    version = version.replace('-', '.')
    vals = version.split('.')
    return [int(x) for x in vals]

def should_skip():
    "Check if tests should be skipped due to old imagemagick version."
    min_version = (6, 9)        # minimum imagemagick version
    try:
        actual_version = get_imagemagick_version()
    except AssertionError:
        return True
    actual_version = tuple(actual_version[:2])
    return actual_version < min_version

pytestmark = pytest.mark.skipif(should_skip(), reason="recent version of imagemagick not found")

TEST_DIR = path.dirname(path.abspath(__file__))
DATA_DIR = path.join(TEST_DIR, 'data')
SVGS = glob(path.join(DATA_DIR, '*', '*.svg'))
metrics = ('AE', 'FUZZ', 'MAE', 'MEPP', 'MSE', 'PAE', 'PHASH', 'PSNR', 'RMSE')
ImgDistortion = namedtuple('ImgDistortion', metrics)

def compare_images(test_img, reference_img, metric='MAE'):
    """Compare images at paths test_img and reference_img

    Use imagemagick to calculate distortion using the given metric.
    You can view the available metrics with 'convert -list metric'.
    """
    cmd = [
        'convert',
        test_img,
        reference_img,
        '-metric',
        metric,
        '-compare',
        '-format',
        '%[distortion]\n',
        'info:'
    ]
    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = p.communicate()
    print('stdout', stdout)
    print('stderr', stderr)
    print('cmd', cmd)
    return float(stdout.decode().strip())

def compare_images_all_metrics(test_img, reference_img):
    """Compare images at paths test_img and reference_img

    Use imagemagick to calculate distortion using all metrics
    listed as fields in ImgDistortion.
    """
    vals = []
    for metric in ImgDistortion._fields:
        vals.append(compare_images(test_img, reference_img, metric))
    return ImgDistortion._make(vals)

@pytest.fixture(scope='function', params=SVGS)
def svg_img(request):
    "svg_img returns an instance of libqtile.images.Img()"
    fpath = request.param
    return images.Img.from_path(fpath)

@pytest.fixture(scope='function')
def comparison_images(svg_img):
    "Return a tuple of paths to the bad and good comparison images, respectively."
    name = svg_img.name
    path_good = path.join(DATA_DIR, 'comparison_images', name+'_good.png')
    path_bad = path.join(DATA_DIR, 'comparison_images', name+'_bad.png')
    return path_bad, path_good
    
@pytest.fixture(scope='function')
def distortion_bad(svg_img, comparison_images):
    path_bad, path_good = comparison_images
    name = svg_img.name
    return compare_images_all_metrics(path_bad, path_good)

def assert_distortion_less_than(distortion, bad_distortion, factor=0.3):
    for test_val, bad_val in zip(distortion, bad_distortion):
        assert test_val < (bad_val * factor)

def test_svg_scaling(svg_img, distortion_bad, comparison_images, tmpdir):
    path_bad, path_good = comparison_images
    scaling_factor = 20
    print(svg_img.path)
    print(distortion_bad)
    print(tmpdir.dirpath())
    dpath = tmpdir.dirpath

    name = svg_img.name
    svg_img.scale(width_factor=20, lock_aspect_ratio=True)
    surf = cairocffi.SVGSurface(str(dpath(name+'.svg')), svg_img.width, svg_img.height)
    ctx = cairocffi.Context(surf)

    ctx.save()
    ctx.set_source(svg_img.pattern)
    ctx.paint()
    ctx.restore()

    test_png_path = str(dpath(name+'.png'))
    surf.write_to_png(test_png_path)
    surf.finish()
    distortion = compare_images_all_metrics(test_png_path, path_good)
    assert_distortion_less_than(distortion, distortion_bad)
