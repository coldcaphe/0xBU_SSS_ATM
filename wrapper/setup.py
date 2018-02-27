from distutils.core import setup, Extension

setup(
        ext_modules=[Extension("crypto", ["../libhydrogen/hydrogen.c", "cryptowrapper.c"])]
    )
