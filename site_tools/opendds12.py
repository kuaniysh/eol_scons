#
# Tool for OpenDDS version 1.2 and greater.  
# This will set up appropriate paths to find OpenDDS headers 
# and libraries and build the DDS support library.
#
import os
import string
import re
from eol_scons.chdir import ChdirActions
from SCons.Options import PathOption

_options = None
mykey = "HAS_PKG_OPENDDS"

def generate(env):

  global _options
  if not _options:
    _options = env.GlobalOptions()
    dds_root = env.FindPackagePath('DDS_ROOT', '$OPT_PREFIX/OpenDDS*')
    _options.AddOptions(PathOption('DDS_ROOT', 'DDS_ROOT directory.', dds_root))
  _options.Update(env)
  
  # Use the existence of a key in the env to separate the DDS tool into
  # what need only be applied once and what must be applied every time this
  # tool is Require()d by another package.  Basically that means the library
  # must always be appended; everything else happens once.

  if not env.has_key(mykey):
    env.Require(['tao', 'ace', 'doxygen'])
    
    dds_root = env['DDS_ROOT']
    env['ENV']['DDS_ROOT'] = dds_root
    
    env.AppendUnique(CPPPATH=[dds_root])
    
    libpath=os.path.join(dds_root, 'lib')
    env.Append(LIBPATH=[libpath, ])
    env.AppendUnique(RPATH=[libpath])

    env.AppendDoxref("dds:%s/html/dds" % (dds_root))
    env[mykey] = 1

  env.DdsLibrary = DdsLibrary


def exists(env):
    return True

# 
# A DDS project simply defines one or more
# datatypes that will be handled by DDS. This is
# done in an idl file. A raft of supporting
# code and idl is generated from the original
# idl definition of the datatype.
#
# example usage:
# import os
# import DDSLib
# env = Environment(ENV = os.environ)
# lib = DDSLib.DdsLibrary('EldoraDds.idl', env)
#
# -------------------------------------------
#
# Create a library containing all DDS routines
# required for both server and client
#
# @param idlFile The idl file defining the DDS for a particular type
# #param env 
def DdsLibrary(idlFile, env):
    # get our current directory relative to the top level, needed
    # for some later comands which must be executed here.
    curDir = env.Dir('.').get_path(env.Dir('#'))
    execHerePrefix = "cd %s && " % curDir
    #
    # ------------------------------------------
    #
    # get a list of files produced by the tao_idl processing of
    # the main idl. There will be three sublists:
    #[[*.cpp], [*.h], [*.inl]]
    target1 = taoIdlFiles(idlFile)
    #
    # Now process the main idl file with tao_idl.
    env.Command(target1, idlFile, 
                env['TAO_IDL'] + ' -o $SOURCE.dir -Gdcps $SOURCE')
    #
    # ------------------------------------------
    #
    # get a list of files produced by the dcps_ts processing of
    # the type support idl files. There will be three sublists:
    #[[*.cpp], [*.h], [*.idl]]  (Note the idl output)
    target2 = dcpsTsFiles(idlFile)
    #
    # Process the main idl file with dcps_ts.pl
    # Execute the dcp_tl.pl command in the current directory.
    cmd = os.path.join(env['DDS_ROOT'], 'bin', 'dcps_ts.pl')
    dcpsCmd = ChdirActions(env, [cmd + " $SOURCE.file"], curDir)
    env.Command(target2, idlFile, dcpsCmd)
    #
    # ------------------------------------------
    #
    # Process the generated type support idl file using tao_idl
    tao_cmd = ChdirActions(env, [env['TAO_IDL'] + ' -I ' + env['DDS_ROOT'] +
                                 ' $SOURCE.file'], curDir)
    typeSupportIdlFile = target2[2][0]
    target3 = taoIdlFiles(typeSupportIdlFile)
    env.Command(target3, typeSupportIdlFile, tao_cmd)
    #
    # ------------------------------------------
    #
    # Collect all of the source files, which will be compiled for the
    # library
    sources = target1[0] + target2[0] + target3[0]
    headers = target1[1] + target2[1] + target3[1]
    #
    # library name is the same as the IDL file base name, with the
    # .idl extension removed
    libName = os.path.splitext(os.path.basename(idlFile))[0]
	#
    # Return the library itself, and also a list of source and header files
    # used to generate it (for documentation purposes)
    return [env.Library(libName, sources), sources, headers]

# -------- DDS support functions -----------
#
# Two functions are provided here which generate all of the file names
# associated with a a DDS project. These are taoIdlFiles() and
# dcpsTsFiles(). These functions create all of the filenames that will be
# created by the tao_idl and the dcps_ts.pl processors.
#
# These functions are used by the DsdLibrary() function.
#
# -------------------------------------------
#
# Create the filenames that are produced by tao_idl -Gdcps processing.

# @param idlFile The name of the idl file
# @return A 3 element list. The first slice contains a list of .cpp
# files. The second slice contains a list of .h files. The third slice
# contains a list of .inl files.
def taoIdlFiles(idlFile):
    root     = idlFile.split('.')[0]
    cppFiles = [root+'C.cpp', root+'S.cpp']
    hFiles   = [root+'C.h', root+'S.h']
    inlFiles = [root+'C.inl', root+'S.inl']
    return [cppFiles, hFiles, inlFiles]

# Create the filenames that are produced by dcps_ts.pl processing.
#
# @param idlFile The name of the idl file
# @return A 3 element list. The first slice contains a .cpp
# file. The second slice a .h file. The third slice
# contains an .idl file.
def dcpsTsFiles(idlFile):
    root    = idlFile.split('.')[0]
    cppFile = [root+'TypeSupportImpl.cpp',]
    hFile   = [root+'TypeSupportImpl.h',]
    idlFile = [root+'TypeSupport.idl',]
    return [cppFile, hFile, idlFile]
