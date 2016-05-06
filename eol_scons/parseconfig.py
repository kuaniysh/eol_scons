# -*- python -*-
# Copyright 2007 UCAR, NCAR, All Rights Reserved

import os
import re

from subprocess import *

_debug = False

def _extract_results(text):
    # The string result and integer returncode are coded in the cached
    # string as '<returncode>,<resultstring>'.  Sometimes the result
    # strings have more than one line, so we must be careful to extract the
    # rest of the string, including any newlines.
    m = re.match(r"^([-+]?\d+),", text)
    if m:
        return (int(m.group(1)), text[m.end():])
    else:
        return (-1, text)


def getConfigCache(env):
    cache = env.get("_config_cache")
    if cache is None:
        cache = {}
        env["_config_cache"] = cache
    return cache


def _get_config(env, search_paths, config_script, args):
    """
    Return a (returncode, output) tuple for a call to @p config_script.

    By collecting both the return code and the output result from the same
    call to the config script, it is not necessary to first call the config
    script just to test whether the package's config script is installed.
    If there is a non-zero return code from the config script command, then
    tools can continue with other methods of configuring the tool.

    The config results are cached in the calling Environment, so the
    command does not need to be run every time a tool needs to run the same
    config script.  However, the results are specific to the Environment,
    since the results can change depending upon the Environment running
    them.  For example, PKG_CONFIG_PATH might be different for different
    environments, and cross-build environments will return different
    results.  The goal is to avoid redundant runs of the same config script
    when called for the same environment, such as redundant applications of
    the same tool.
    """
    result = None
    if _debug: print("_get_config(%s,%s): " % (config_script, ",".join(args)))
    # See if the output for this config script call has already been cached.
    name = re.sub(r'[^\w]', '_', config_script + " ".join(args))
    cache = getConfigCache(env)
    result = cache.get(name)
    if result:
        if _debug: print("  cached: %s" % (result))
        return _extract_results(result)
    if not result:
        if search_paths:
            search_paths = [ p for p in search_paths if os.path.exists(p) ]
            env.LogDebug("Checking for %s in %s" % 
                         (config_script, ",".join(search_paths)))
            config = env.WhereIs(config_script, search_paths)
        else:
            config = config_script
        env.LogDebug("Found: %s" % config)
    if not result and config:
        child = Popen([config] + args, stdout=PIPE, env=env['ENV'])
        result = child.communicate()[0].strip()
        cache[name] = "%s,%s" % (child.returncode, result)
        result = (child.returncode, result)
    if not result:
        result = (-1, "")
    if _debug: print("   command: %s" % (str(result)))
    return result


def RunConfig(env, command):
    """
    Run the config script command and return tuple (returncode, output).
    """
    args = command.split()
    config_script = args[0]
    args = args[1:]
    return _get_config(env, None, config_script, args)[1]


def CheckConfig(env, command):
    """
    Return True if the pkg-config-like command succeeds (returns 0).

    The output is cached in the environment, so subsequent requests for the
    same config command will not need to execute the command again.
    """
    args = command.split()
    config_script = args[0]
    args = args[1:]
    return _get_config(env, None, config_script, args)[0] == 0


def ParseConfig(env, command, function=None, unique=True):
    """
    Like Environment.ParseConfig, except do not raise OSError if the
    command fails, and the config script results are cached in the
    Environment.  If the command succeeds, then merge the results flags
    into the Environment and return True.  Otherwise return False.
    """
    args = command.split()
    result = _get_config(env, None, args[0], args[1:])
    if result[0] == 0:
        if not function:
            env.MergeFlags(result[1], unique)
        else:
            function(result[1], unique)
        return True
    return False


def _filter_ldflags(flags):
    "Fix ldflags from config scripts which return standard library dirs."
    fields = flags.split()
    fields = [ f for f in fields if not re.match(r'^-L/usr/lib(64)?$', f) ]
    flags = " ".join(fields)
    return flags


def ParseConfigPrefix(env, config_script, search_prefixes,
                      default_prefix = "$OPT_PREFIX", apply_config = False):
    """Search for a config script and parse the output."""
    search_paths = [ os.path.join(env.subst(x),"bin")
                     for x in [ y for y in search_prefixes if y ] ]
    if search_paths:
        search_paths = [ p for p in search_paths if os.path.exists(p) ]
    prefix = default_prefix
    if env['PLATFORM'] == 'win32':    
        return prefix

    prefix = _get_config(env, search_paths, config_script, ['--prefix'])[1]
    if apply_config:
        flags = _get_config(env, search_paths, config_script,
                            ['--cppflags', '--ldflags', '--libs'])[1]
        if flags:
            if _debug: print("Merging " + flags)
            flags = _filter_ldflags(flags)
            env.MergeFlags(flags)
        else:
            if _debug: print("No flags from %s" % (config_script))
        ldflags = _get_config(env, search_paths, config_script,
                              ['--ldflags'])[1]
        ldflags = _filter_ldflags(ldflags)
                              
        if ldflags:
            ldflags = ldflags.split()
            for flag in ldflags:
                if flag.find('-L') != -1:
                    if (flag.strip().index('-L') == 0):
                        # remove the -L to get the directory, and make the
                        # resulting path absolute
                        dir = os.path.abspath(flag.replace('-L', ''))
                        env.Append(RPATH=dir)
    return prefix


def PkgConfigPrefix(env, pkg_name, default_prefix = "$OPT_PREFIX"):
    """Search for a config script and parse the output."""
    search_prefixes = ['/usr']
    search_paths = [ os.path.join(env.subst(x),"bin")
                     for x in filter(lambda y: y, search_prefixes) ]
    prefix = None
    if env['PLATFORM'] != 'win32':    
        prefix = _get_config(env, search_paths, 'pkg-config',
                             ["--variable=prefix", pkg_name])[1]
    if not prefix:
        prefix = default_prefix
    return prefix


