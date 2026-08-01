# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0](https://github.com/AlteredCraft/chat-rag-explorer/compare/chat-rag-explorer-v0.3.0...chat-rag-explorer-v0.4.0) (2026-08-01)


### Features

* add Ollama (local and cloud) as an LLM provider ([15f19d6](https://github.com/AlteredCraft/chat-rag-explorer/commit/15f19d6fc16e453b5bd1d0d3e0d261cd5f5fab06)), closes [#28](https://github.com/AlteredCraft/chat-rag-explorer/issues/28)
* capture misconfiguration errors and show helpful messages ([6c99adb](https://github.com/AlteredCraft/chat-rag-explorer/commit/6c99adb4ec5529997f54f85875f3f00009c60b0e))


### Bug Fixes

* correct typo in ingest corpus selection prompt ([2ba1a0d](https://github.com/AlteredCraft/chat-rag-explorer/commit/2ba1a0d0dc910245b543ebbe5b531fb9b613c0cc))
* escape server-provided values before innerHTML rendering ([20c1245](https://github.com/AlteredCraft/chat-rag-explorer/commit/20c1245ed545031e9ec175c1fdeee0ecf328cc87)), closes [#27](https://github.com/AlteredCraft/chat-rag-explorer/issues/27)
* warn at startup on unsupported LLM_PROVIDER and clarify provider docs ([1568bcb](https://github.com/AlteredCraft/chat-rag-explorer/commit/1568bcbd8f21e0fa3cbebe71c578919568071bee))


### Documentation

* correct doc/code mismatches and surface the shipped corpora ([3d0439a](https://github.com/AlteredCraft/chat-rag-explorer/commit/3d0439aceec3ec5bc8330bb61f48c56ad7be3f67))

## [0.3.0](https://github.com/AlteredCraft/chat-rag-explorer/compare/chat-rag-explorer-v0.2.1...chat-rag-explorer-v0.3.0) (2026-08-01)


### Features

* add LLM provider seam and simplify services, routes, and streaming ([fc120a0](https://github.com/AlteredCraft/chat-rag-explorer/commit/fc120a09176d371adc1f3488777e8cefea11b6cb))


### Bug Fixes

* align default model across backend, frontend, and models list ([db21153](https://github.com/AlteredCraft/chat-rag-explorer/commit/db211535fba6f231a05996d179af257004a548c7))
* read and write text as UTF-8 for Windows compatibility ([0c4315e](https://github.com/AlteredCraft/chat-rag-explorer/commit/0c4315e4ff17c7776559e0f69276e037f8fa28e4))


### Documentation

* document DEFAULT_MODEL and .models_list usage ([48f0a18](https://github.com/AlteredCraft/chat-rag-explorer/commit/48f0a18c013eb84fb275b945f97980a9141735ab))
* rework for self-serve onboarding and correct stale facts ([ac68ec4](https://github.com/AlteredCraft/chat-rag-explorer/commit/ac68ec417bacafb48d2ad5724edbeb2765129e2d))
* strengthen onboarding with key-verification guidance and troubleshooting ([ac2040e](https://github.com/AlteredCraft/chat-rag-explorer/commit/ac2040ebf893ab633c5b64c72203329eda46fb50))

## [0.2.1](https://github.com/AlteredCraft/chat-rag-explorer/compare/chat-rag-explorer-v0.2.0...chat-rag-explorer-v0.2.1) (2026-07-30)


### Bug Fixes

* cover full document when chunking by tokens ([565c116](https://github.com/AlteredCraft/chat-rag-explorer/commit/565c11682d2add4d18b239d8ed9b7f9cbbb83a09))

## [0.2.0](https://github.com/AlteredCraft/chat-rag-explorer/compare/chat-rag-explorer-v0.1.0...chat-rag-explorer-v0.2.0) (2026-02-03)


### Features

* add Release Please for automated versioning and changelog ([1bbca36](https://github.com/AlteredCraft/chat-rag-explorer/commit/1bbca367e59da1e73b0cd2b38fa5eb78389705fd))
