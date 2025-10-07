cmake_minimum_required(VERSION 3.16)
project(TagFileBrowser NONE)

# This CMake script packages the Tkinter app into a single-file executable using PyInstaller.
# Usage:
#   cmake -S . -B build
#   cmake --build build --target dist
#
# Result:
#   build/dist/TagFileBrowser (or TagFileBrowser.exe on Windows)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(MAIN_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/src/tag_file_browser.py)

# Allow overriding the exe name: -DAPP_NAME=MyApp
if(NOT DEFINED APP_NAME)
  set(APP_NAME TagFileBrowser)
endif()

add_custom_target(dist ALL
  COMMAND ${Python3_EXECUTABLE} -m pip install --upgrade pip
  COMMAND ${Python3_EXECUTABLE} -m pip install pyinstaller
  # --windowed disables console on Windows/macOS. Remove it if you want a console window.
  COMMAND ${Python3_EXECUTABLE} -m PyInstaller --noconfirm --onefile --windowed --name ${APP_NAME} ${MAIN_SCRIPT}
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  COMMENT "Building single-file executable with PyInstaller"
)
