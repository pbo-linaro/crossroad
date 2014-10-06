# the name of the target operating system
# SET(CMAKE_SYSTEM_NAME Android)
# See http://comments.gmane.org/gmane.comp.programming.tools.cmake.user/49795
# The Platform/Android.cmake file appeared in March of 2014 in dev code.
# http://www.cmake.org/gitweb?p=cmake.git;a=history;f=Modules/Platform/Android.cmake
# No released version yet. Use the Linux platform.
SET(CMAKE_SYSTEM_NAME Linux)

# This is not a usual cmake variable. Simply some projects seem to use this to detect
# an Android build and special-casing.
# Probably because CMAKE_SYSTEM_NAME cannot be Android yet...
SET(ANDROID TRUE)
# Allegro needs both ANDROID and WANT_ANDROID set.
SET(WANT_ANDROID TRUE)

# which compilers to use for C and C++
SET(CMAKE_C_COMPILER arm-linux-androideabi-gcc)
SET(CMAKE_CXX_COMPILER arm-linux-androideabi-g++)

# here is the target environment located
SET(CMAKE_FIND_ROOT_PATH $ENV{CROSSROAD_PREFIX} /usr/local/arm-linux-androideabi/ /usr/arm-linux-androideabi/)

# adjust the default behaviour of the FIND_XXX() commands:
# search headers and libraries in the target environment, search
# programs in the host environment
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
