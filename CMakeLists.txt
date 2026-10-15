cmake_minimum_required(VERSION 3.16)
project(delphi_hepmc_converter LANGUAGES CXX)

# Build the external-event converter without key4hep, CVMFS, or CMSSW.
find_package(HepMC3 3.3 CONFIG REQUIRED HINTS
    "$ENV{HEPMC3_PREFIX}"
    "$ENV{HOME}/.local/opt/hepmc3/3.3.1")
add_executable(hepmc2fadgen hepmc2fadgen.cpp)
target_compile_features(hepmc2fadgen PRIVATE cxx_std_17)
target_link_libraries(hepmc2fadgen PRIVATE HepMC3::HepMC3)
set_target_properties(hepmc2fadgen PROPERTIES INSTALL_RPATH_USE_LINK_PATH TRUE)
install(TARGETS hepmc2fadgen RUNTIME DESTINATION bin)

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(make_smoke_events tests/make_smoke_events.cpp)
    target_compile_features(make_smoke_events PRIVATE cxx_std_17)
    target_link_libraries(make_smoke_events PRIVATE HepMC3::HepMC3)
    add_test(NAME hepmc_fadgen_roundtrip
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_conversion.py"
        "$<TARGET_FILE:make_smoke_events>" "$<TARGET_FILE:hepmc2fadgen>")
endif()
