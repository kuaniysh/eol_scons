import os,os.path, sys
import SCons

def generate(env):
    if env['PLATFORM'] != 'darwin':
        env.Append (LIBS = ["boost_date_time"])
    else:
        env.Append (LIBS = ["boost_date_time-mt"])
    libpath = os.path.abspath(os.path.join(env['OPT_PREFIX'],'lib'))
    env.AppendUnique(LIBPATH=[libpath])

def exists(env):
    return True

