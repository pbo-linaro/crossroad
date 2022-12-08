# the name of the target operating system
SET(CMAKE_SYSTEM_NAME Windows)

# which compilers to use for C and C++
SET(CMAKE_C_COMPILER aarch64-w64-mingw32-gcc)
SET(CMAKE_CXX_COMPILER aarch64-w64-mingw32-g++)
SET(CMAKE_RC_COMPILER aarch64-w64-mingw32-windres)

# This value is not set automatically when cross-compiling with CMake.
# According to CMake doc, it would usually be set to the value of
# PROCESSOR_ARCHITECTURE environment variable when natively compiling on
# win32. Finally according to information I could find, this variable
# would be "x86" for 32-bit, "AMD64" for 64-bit and "arm64" for Arm 64-bit.
SET(CMAKE_SYSTEM_PROCESSOR arm64)

# here is the target environment located
SET(CMAKE_FIND_ROOT_PATH $ENV{CROSSROAD_PREFIX} $ENV{CROSSROAD_CUSTOM_MINGW_W64_PREFIX} $ENV{CROSSROAD_GUESSED_MINGW_PREFIX} /usr/local/aarch64-w64-mingw32 /usr/aarch64-w64-mingw32)

# adjust the default behaviour of the FIND_XXX() commands:
# search headers and libraries in the target environment, search
# programs in the host environment
SET(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
SET(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
SET(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
