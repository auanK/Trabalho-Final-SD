{
  "targets": [
    {
      "target_name": "voip_addon",

      "sources": [
        "src/addon_main.cpp",
        "src/voip_client.cpp",
        "src/audio_engine.cpp"
      ],

      "defines": [
        "NAPI_VERSION=<(napi_build_version)"
      ],

      "conditions": [
        [ 'OS=="win"', {
          "include_dirs": [
            "node_modules/node-addon-api",
            "include",
            "<(VCPKG_ROOT)/installed/x64-windows-static-md/include"
          ],

          "defines": [ "PA_STATIC" ],
          "library_dirs": [
            "<(VCPKG_ROOT)/installed/x64-windows-static-md/lib"
          ],
          "libraries": [
            "opus.lib", "portaudio.lib", "legacy_stdio_definitions.lib",
            "ucrt.lib", "Ws2_32.lib", "Winmm.lib", "Ole32.lib",
            "OleAut32.lib", "SetupAPI.lib"
          ],
          "msvs_settings": {
            "VCCLCompilerTool": {
              "ExceptionHandling": 1,
              "RuntimeLibrary": 2,
              "AdditionalOptions": [ "/std:c++17", "/W4" ]
            },
            "VCLinkerTool": {
              "AdditionalOptions": [
                "/NODEFAULTLIB:MSVCRT.lib",
                "/NODEFAULTLIB:libucrt.lib"
              ]
            }
          }
        }],

        [ 'OS=="linux"', {
          "include_dirs": [
            "node_modules/node-addon-api",
            "include"
          ],
          "defines": [
            "NODE_ADDON_API_CPP_EXCEPTIONS=1"
          ],
          "libraries": [
            "-lportaudio",
            "-lopus",
            "-lpthread"
          ],
          "cflags_cc": [
            "-std=c++17",
            "-O2",
            "-fexceptions",
            "-frtti"
          ]
        }]
      ]
    }
  ]
}
