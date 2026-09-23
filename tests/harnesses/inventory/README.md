# Observed harness environments

Variables present in each harness's Linux command environment, including inherited configuration. Values are captured exactly from isolated mock runs, including dummy API keys and generated session IDs. The table uses JSON string notation to preserve whitespace and empty strings.

Generated from verified probes. Test results and execution details live in the CI artifacts; the detector does not read this inventory.

## claude-code

| Variable | Value |
| --- | --- |
| `AI_AGENT` | <code>&quot;claude-code_2-1-281_agent&quot;</code> |
| `ANTHROPIC_API_KEY` | <code>&quot;not-a-secret&quot;</code> |
| `ANTHROPIC_BASE_URL` | <code>&quot;http://gateway:8080&quot;</code> |
| `CLAUDECODE` | <code>&quot;1&quot;</code> |
| `CLAUDE_CODE_CHILD_SESSION` | <code>&quot;1&quot;</code> |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | <code>&quot;1&quot;</code> |
| `CLAUDE_CODE_ENTRYPOINT` | <code>&quot;sdk-cli&quot;</code> |
| `CLAUDE_CODE_EXECPATH` | <code>&quot;/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe&quot;</code> |
| `CLAUDE_CODE_SESSION_ATTENDED` | <code>&quot;0&quot;</code> |
| `CLAUDE_CODE_SESSION_ID` | <code>&quot;47b561fc-ef57-4c04-9409-3584b5264245&quot;</code> |
| `CLAUDE_CODE_SIMPLE` | <code>&quot;1&quot;</code> |
| `CLAUDE_EFFORT` | <code>&quot;high&quot;</code> |
| `CLAUDE_PID` | <code>&quot;1&quot;</code> |
| `COREPACK_ENABLE_AUTO_PIN` | <code>&quot;0&quot;</code> |
| `DISABLE_AUTOUPDATER` | <code>&quot;1&quot;</code> |
| `GIT_EDITOR` | <code>&quot;true&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;3017fb14e3f2&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `NoDefaultCurrentDirectoryInExePath` | <code>&quot;1&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHELL` | <code>&quot;/bin/bash&quot;</code> |
| `SHLVL` | <code>&quot;1&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## cline

| Variable | Value |
| --- | --- |
| `CLINE_CONNECTOR_CLI_LAUNCH` | <code>&quot;{\&quot;launcher\&quot;:\&quot;/usr/local/lib/node_modules/cline/bin/.cline\&quot;,\&quot;connectArgsPrefix\&quot;:[\&quot;connect\&quot;],\&quot;cwd\&quot;:\&quot;/work\&quot;}&quot;</code> |
| `CLINE_WRAPPER_PATH` | <code>&quot;/usr/local/lib/node_modules/cline/bin/cline&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;69ca3c2f0624&quot;</code> |
| `NODE_EXTRA_CA_CERTS` | <code>&quot;/tmp/.cline/cli-node-extra-ca-certs.pem&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## codex

| Variable | Value |
| --- | --- |
| `CODEX_CI` | <code>&quot;1&quot;</code> |
| `CODEX_MANAGED_BY_NPM` | <code>&quot;1&quot;</code> |
| `CODEX_MANAGED_PACKAGE_ROOT` | <code>&quot;/usr/local/lib/node_modules/@openai/codex&quot;</code> |
| `CODEX_SESSION_ID` | <code>&quot;01a0cfff-a19f-7700-9212-ee88f615575d&quot;</code> |
| `CODEX_THREAD_ID` | <code>&quot;01a0cfff-a19f-7700-9212-ee88f615575d&quot;</code> |
| `CODEX_VERSION` | <code>&quot;0.156.1&quot;</code> |
| `COLORTERM` | <code>&quot;&quot;</code> |
| `GH_PAGER` | <code>&quot;cat&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;0cc94fa452b9&quot;</code> |
| `LANG` | <code>&quot;C.UTF-8&quot;</code> |
| `LC_ALL` | <code>&quot;C.UTF-8&quot;</code> |
| `LC_CTYPE` | <code>&quot;C.UTF-8&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `NO_COLOR` | <code>&quot;1&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-path:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `TERM` | <code>&quot;dumb&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## crush

| Variable | Value |
| --- | --- |
| `AGENT` | <code>&quot;crush&quot;</code> |
| `AI_AGENT` | <code>&quot;crush&quot;</code> |
| `CRUSH` | <code>&quot;1&quot;</code> |
| `CRUSH_DISABLE_METRICS` | <code>&quot;1&quot;</code> |
| `CRUSH_DISABLE_PROVIDER_AUTO_UPDATE` | <code>&quot;1&quot;</code> |
| `DISABLE_METRICS` | <code>&quot;&quot;</code> |
| `DISABLE_PROVIDER_AUTO_UPDATE` | <code>&quot;&quot;</code> |
| `DO_NOT_TRACK` | <code>&quot;1&quot;</code> |
| `EDITOR` | <code>&quot;false&quot;</code> |
| `GIT_EDITOR` | <code>&quot;false&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;80efeb69d9a8&quot;</code> |
| `JJ_EDITOR` | <code>&quot;false&quot;</code> |
| `JJ_PAGER` | <code>&quot;cat&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `TERM` | <code>&quot;xterm-256color&quot;</code> |
| `VISUAL` | <code>&quot;false&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |

## deepseek-harness

| Variable | Value |
| --- | --- |
| `DSH_HOME` | <code>&quot;/tmp/dsh&quot;</code> |
| `DSH_SESSION_ID` | <code>&quot;session-23ef8aae-e4d0-482d-90ef-439814cd28e2&quot;</code> |
| `DSH_SHELL` | <code>&quot;1&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;f51a94cac930&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `NO_COLOR` | <code>&quot;1&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `TERM` | <code>&quot;dumb&quot;</code> |
| `VIPSHOME` | <code>&quot;/target&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## gemini-cli

| Variable | Value |
| --- | --- |
| `DBUS_SESSION_BUS_ADDRESS` | <code>&quot;&quot;</code> |
| `DISPLAY` | <code>&quot;&quot;</code> |
| `GCM_INTERACTIVE` | <code>&quot;never&quot;</code> |
| `GEMINI_API_KEY` | <code>&quot;not-a-secret&quot;</code> |
| `GEMINI_CLI` | <code>&quot;1&quot;</code> |
| `GEMINI_CLI_NO_RELAUNCH` | <code>&quot;true&quot;</code> |
| `GEMINI_CLI_TRUST_WORKSPACE` | <code>&quot;true&quot;</code> |
| `GH_PROMPT_DISABLED` | <code>&quot;1&quot;</code> |
| `GIT_ASKPASS` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_COUNT` | <code>&quot;8&quot;</code> |
| `GIT_CONFIG_GLOBAL` | <code>&quot;/dev/null&quot;</code> |
| `GIT_CONFIG_KEY_0` | <code>&quot;credential.helper&quot;</code> |
| `GIT_CONFIG_KEY_1` | <code>&quot;core.fsmonitor&quot;</code> |
| `GIT_CONFIG_KEY_2` | <code>&quot;core.hooksPath&quot;</code> |
| `GIT_CONFIG_KEY_3` | <code>&quot;core.sshCommand&quot;</code> |
| `GIT_CONFIG_KEY_4` | <code>&quot;core.pager&quot;</code> |
| `GIT_CONFIG_KEY_5` | <code>&quot;core.editor&quot;</code> |
| `GIT_CONFIG_KEY_6` | <code>&quot;sequence.editor&quot;</code> |
| `GIT_CONFIG_KEY_7` | <code>&quot;diff.external&quot;</code> |
| `GIT_CONFIG_NOSYSTEM` | <code>&quot;1&quot;</code> |
| `GIT_CONFIG_SYSTEM` | <code>&quot;/dev/null&quot;</code> |
| `GIT_CONFIG_VALUE_0` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_1` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_2` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_3` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_4` | <code>&quot;cat&quot;</code> |
| `GIT_CONFIG_VALUE_5` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_6` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_VALUE_7` | <code>&quot;&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `GIT_TERMINAL_PROMPT` | <code>&quot;0&quot;</code> |
| `GOOGLE_GEMINI_BASE_URL` | <code>&quot;http://127.0.0.1:8080&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;f25d7590e3b6&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;1&quot;</code> |
| `SSH_ASKPASS` | <code>&quot;&quot;</code> |
| `TERM` | <code>&quot;xterm-256color&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## github-copilot

| Variable | Value |
| --- | --- |
| `COPILOT_AGENT_SESSION_ID` | <code>&quot;57c2406f-5507-4730-b350-2a54b31bc107&quot;</code> |
| `COPILOT_CLI` | <code>&quot;1&quot;</code> |
| `COPILOT_CLI_BINARY_VERSION` | <code>&quot;1.0.88&quot;</code> |
| `COPILOT_CLI_RESOLVED_DIST_DIR` | <code>&quot;/tmp/cache/copilot/pkg/linux-x64/1.0.88&quot;</code> |
| `GCM_INTERACTIVE` | <code>&quot;Never&quot;</code> |
| `GIT_ASKPASS` | <code>&quot;&quot;</code> |
| `GIT_CONFIG_COUNT` | <code>&quot;3&quot;</code> |
| `GIT_CONFIG_KEY_0` | <code>&quot;safe.bareRepository&quot;</code> |
| `GIT_CONFIG_KEY_1` | <code>&quot;credential.interactive&quot;</code> |
| `GIT_CONFIG_KEY_2` | <code>&quot;core.fsmonitor&quot;</code> |
| `GIT_CONFIG_VALUE_0` | <code>&quot;explicit&quot;</code> |
| `GIT_CONFIG_VALUE_1` | <code>&quot;never&quot;</code> |
| `GIT_CONFIG_VALUE_2` | <code>&quot;&quot;</code> |
| `GIT_OPTIONAL_LOCKS` | <code>&quot;0&quot;</code> |
| `GIT_TERMINAL_PROMPT` | <code>&quot;0&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;7696e93f1993&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `SSH_ASKPASS` | <code>&quot;&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## goose

| Variable | Value |
| --- | --- |
| `AGENT_SESSION_ID` | <code>&quot;20260923_1&quot;</code> |
| `GOOSE_DISABLE_KEYRING` | <code>&quot;1&quot;</code> |
| `GOOSE_MAX_TURNS` | <code>&quot;3&quot;</code> |
| `GOOSE_MODE` | <code>&quot;auto&quot;</code> |
| `GOOSE_MODEL` | <code>&quot;probe-model&quot;</code> |
| `GOOSE_PROVIDER` | <code>&quot;openai&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;9019f2b7173c&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OPENAI_API_KEY` | <code>&quot;not-a-secret&quot;</code> |
| `OPENAI_HOST` | <code>&quot;http://gateway:8080&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## hermes-agent

| Variable | Value |
| --- | --- |
| `AI_AGENT` | <code>&quot;hermes-agent&quot;</code> |
| `BROWSER_INACTIVITY_TIMEOUT` | <code>&quot;120&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `HERMES_AGENT` | <code>&quot;true&quot;</code> |
| `HERMES_HOME` | <code>&quot;/tmp/hermes&quot;</code> |
| `HERMES_INTERACTIVE` | <code>&quot;1&quot;</code> |
| `HERMES_KANBAN_BOARD` | <code>&quot;default&quot;</code> |
| `HERMES_QUIET` | <code>&quot;1&quot;</code> |
| `HERMES_REAL_HOME` | <code>&quot;/tmp&quot;</code> |
| `HERMES_SCRATCH_DIR` | <code>&quot;/tmp/hermes/cache/scratch&quot;</code> |
| `HERMES_SESSION_ID` | <code>&quot;20260923_204143_50158c&quot;</code> |
| `HERMES_SINGLE_QUERY_SESSION` | <code>&quot;1&quot;</code> |
| `HERMES_TURN_LEASE_TIMEOUT` | <code>&quot;5&quot;</code> |
| `HERMES_YOLO_MODE` | <code>&quot;true&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;b6efb246eabe&quot;</code> |
| `LC_CTYPE` | <code>&quot;C.UTF-8&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OLDPWD` | <code>&quot;/work&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;1&quot;</code> |
| `SSL_CERT_FILE` | <code>&quot;/usr/lib/ssl/cert.pem&quot;</code> |
| `TEMP` | <code>&quot;/tmp/hermes/cache/scratch&quot;</code> |
| `TERMINAL_CONTAINER_CPU` | <code>&quot;1&quot;</code> |
| `TERMINAL_CONTAINER_DISK` | <code>&quot;51200&quot;</code> |
| `TERMINAL_CONTAINER_MEMORY` | <code>&quot;5120&quot;</code> |
| `TERMINAL_CONTAINER_PERSISTENT` | <code>&quot;True&quot;</code> |
| `TERMINAL_CWD` | <code>&quot;/work&quot;</code> |
| `TERMINAL_DAYTONA_IMAGE` | <code>&quot;nikolaik/python-nodejs:python3.11-nodejs20&quot;</code> |
| `TERMINAL_DEGRADED_MODE` | <code>&quot;warn&quot;</code> |
| `TERMINAL_DOCKER_ENV` | <code>&quot;{}&quot;</code> |
| `TERMINAL_DOCKER_EXTRA_ARGS` | <code>&quot;[]&quot;</code> |
| `TERMINAL_DOCKER_FORWARD_ENV` | <code>&quot;[]&quot;</code> |
| `TERMINAL_DOCKER_IMAGE` | <code>&quot;nikolaik/python-nodejs:python3.11-nodejs20&quot;</code> |
| `TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE` | <code>&quot;False&quot;</code> |
| `TERMINAL_DOCKER_NETWORK` | <code>&quot;True&quot;</code> |
| `TERMINAL_DOCKER_RUN_AS_HOST_USER` | <code>&quot;False&quot;</code> |
| `TERMINAL_DOCKER_SHARED_CONTAINER_KEY` | <code>&quot;&quot;</code> |
| `TERMINAL_DOCKER_SHM_SIZE` | <code>&quot;1g&quot;</code> |
| `TERMINAL_DOCKER_SNAP_COMPAT` | <code>&quot;False&quot;</code> |
| `TERMINAL_DOCKER_VOLUMES` | <code>&quot;[]&quot;</code> |
| `TERMINAL_ENV` | <code>&quot;local&quot;</code> |
| `TERMINAL_HOME_MODE` | <code>&quot;auto&quot;</code> |
| `TERMINAL_LIFETIME_SECONDS` | <code>&quot;300&quot;</code> |
| `TERMINAL_MODAL_IMAGE` | <code>&quot;nikolaik/python-nodejs:python3.11-nodejs20&quot;</code> |
| `TERMINAL_MODAL_MODE` | <code>&quot;auto&quot;</code> |
| `TERMINAL_PERSISTENT_SHELL` | <code>&quot;True&quot;</code> |
| `TERMINAL_SINGULARITY_IMAGE` | <code>&quot;docker://nikolaik/python-nodejs:python3.11-nodejs20&quot;</code> |
| `TERMINAL_TEMP_DIR` | <code>&quot;&quot;</code> |
| `TERMINAL_TIMEOUT` | <code>&quot;30&quot;</code> |
| `TERMINAL_VERCEL_RUNTIME` | <code>&quot;node24&quot;</code> |
| `TMP` | <code>&quot;/tmp/hermes/cache/scratch&quot;</code> |
| `TMPDIR` | <code>&quot;/tmp/hermes/cache/scratch&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |
| `_HERMES_GATEWAY` | <code>&quot;1&quot;</code> |

## junie

| Variable | Value |
| --- | --- |
| `CI` | <code>&quot;1&quot;</code> |
| `DEBIAN_FRONTEND` | <code>&quot;noninteractive&quot;</code> |
| `EJ_RUNNER_PWD` | <code>&quot;/work&quot;</code> |
| `GIT_ASKPASS` | <code>&quot;/bin/false&quot;</code> |
| `GIT_OPTIONAL_LOCKS` | <code>&quot;0&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `GIT_TERMINAL_PROMPT` | <code>&quot;0&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOMEBREW_NO_AUTO_UPDATE` | <code>&quot;1&quot;</code> |
| `HOSTNAME` | <code>&quot;1139b23dbc52&quot;</code> |
| `JUNIE_DATA` | <code>&quot;/opt/junie&quot;</code> |
| `JUNIE_SHIM_PATH` | <code>&quot;/opt/junie-shim&quot;</code> |
| `JUNIE_SKIP_UPDATE_CHECK` | <code>&quot;1&quot;</code> |
| `JUNIE_TMPDIR` | <code>&quot;/tmp/junie/session-260923-204036-7gn6&quot;</code> |
| `LD_LIBRARY_PATH` | <code>&quot;:/opt/junie/versions/3110.7/junie-app/lib/app&quot;</code> |
| `MATTERHORN_SESSION_ID` | <code>&quot;40e25a5e-2c95-440e-85b3-8c6319633755&quot;</code> |
| `MATTERHORN_TASK` | <code>&quot;&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `NO_COLOR` | <code>&quot;1&quot;</code> |
| `NPM_CONFIG_YES` | <code>&quot;true&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PIP_DISABLE_PIP_VERSION_CHECK` | <code>&quot;1&quot;</code> |
| `PIP_NO_INPUT` | <code>&quot;1&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;1&quot;</code> |
| `SSH_ASKPASS` | <code>&quot;/bin/false&quot;</code> |
| `TERM` | <code>&quot;dumb&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |
| `_JPACKAGE_LAUNCHER` | <code>&quot;0&quot;</code> |

## kilo-code

| Variable | Value |
| --- | --- |
| `AGENT` | <code>&quot;1&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;696c0371828e&quot;</code> |
| `KILO` | <code>&quot;1&quot;</code> |
| `KILOCODE_FEATURE` | <code>&quot;cli&quot;</code> |
| `KILOCODE_VERSION` | <code>&quot;7.7.9&quot;</code> |
| `KILO_DISABLE_AUTOUPDATE` | <code>&quot;1&quot;</code> |
| `KILO_DISABLE_MODELS_FETCH` | <code>&quot;1&quot;</code> |
| `KILO_PID` | <code>&quot;28&quot;</code> |
| `KILO_PROCESS_ROLE` | <code>&quot;main&quot;</code> |
| `KILO_RUN_ID` | <code>&quot;e273794a-2864-490b-b44f-e1a4fbc6bb7b&quot;</code> |
| `KILO_TREE_SITTER_WASM_DIR` | <code>&quot;/usr/local/lib/node_modules/@kilocode/cli/bin/tree-sitter&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OPENCODE` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_AUTOUPDATE` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_MODELS_FETCH` | <code>&quot;1&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## openclaw

| Variable | Value |
| --- | --- |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;b30c9bf43b38&quot;</code> |
| `NODE_NO_WARNINGS` | <code>&quot;1&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OPENCLAW_CLI` | <code>&quot;1&quot;</code> |
| `OPENCLAW_NODE_OPTIONS_READY` | <code>&quot;1&quot;</code> |
| `OPENCLAW_PATH_BOOTSTRAPPED` | <code>&quot;1&quot;</code> |
| `OPENCLAW_SHELL` | <code>&quot;exec&quot;</code> |
| `OPENCLAW_STATE_DIR` | <code>&quot;/tmp/openclaw-agent-exec-zzgO1L&quot;</code> |
| `OPENCLAW_WORKSPACE_DIR` | <code>&quot;/work&quot;</code> |
| `PATH` | <code>&quot;/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/usr/local/sbin:/usr/sbin:/sbin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |

## opencode

| Variable | Value |
| --- | --- |
| `AGENT` | <code>&quot;1&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;f03533340f8d&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OPENCODE` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_AUTOCOMPACT` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_AUTOUPDATE` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_FFF` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_MODELS_FETCH` | <code>&quot;1&quot;</code> |
| `OPENCODE_DISABLE_PROJECT_CONFIG` | <code>&quot;1&quot;</code> |
| `OPENCODE_PID` | <code>&quot;1&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |
| `npm_config_user_agent` | <code>&quot;npm/undefined node/v24.3.0 linux x64 workspaces/false&quot;</code> |

## pi

| Variable | Value |
| --- | --- |
| `AI_AGENT` | <code>&quot;pi&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;25a8c4261454&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `PATH` | <code>&quot;/tmp/pi/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PI_CODING_AGENT` | <code>&quot;true&quot;</code> |
| `PI_CODING_AGENT_DIR` | <code>&quot;/tmp/pi&quot;</code> |
| `PI_MODEL` | <code>&quot;probe-model&quot;</code> |
| `PI_OFFLINE` | <code>&quot;1&quot;</code> |
| `PI_PROVIDER` | <code>&quot;harness-test&quot;</code> |
| `PI_REASONING_LEVEL` | <code>&quot;off&quot;</code> |
| `PI_SESSION_ID` | <code>&quot;01a0cfff-a4a4-744d-a788-8bfa614c46be&quot;</code> |
| `PI_SKIP_VERSION_CHECK` | <code>&quot;1&quot;</code> |
| `PI_TELEMETRY` | <code>&quot;0&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## qwen-code

| Variable | Value |
| --- | --- |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;38450d27741f&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `OPENAI_API_KEY` | <code>&quot;not-a-secret&quot;</code> |
| `OPENAI_BASE_URL` | <code>&quot;http://gateway:8080/v1&quot;</code> |
| `OPENAI_MODEL` | <code>&quot;probe-model&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `QWEN_CODE` | <code>&quot;1&quot;</code> |
| `QWEN_CODE_AGENT_ID` | <code>&quot;&quot;</code> |
| `QWEN_CODE_CLI` | <code>&quot;/usr/local/lib/node_modules/@qwen-code/qwen-code/cli-entry.js&quot;</code> |
| `QWEN_CODE_LAUNCHER_PID` | <code>&quot;1&quot;</code> |
| `QWEN_CODE_MANAGED_NPM_PIN` | <code>&quot;{\&quot;bootstrap\&quot;:\&quot;/usr/local/lib/node_modules/@qwen-code/qwen-code/cli-entry.js\&quot;,\&quot;version\&quot;:null,\&quot;updateRoot\&quot;:\&quot;/tmp/.qwen/updates/npm\&quot;}&quot;</code> |
| `QWEN_CODE_MANAGED_NPM_ROOT` | <code>&quot;/tmp/.qwen/updates/npm&quot;</code> |
| `QWEN_CODE_MODEL` | <code>&quot;probe-model&quot;</code> |
| `QWEN_CODE_MODEL_IDENTITY` | <code>&quot;probe-model@64060875&quot;</code> |
| `QWEN_CODE_NO_RELAUNCH` | <code>&quot;true&quot;</code> |
| `QWEN_CODE_PRIVATE_RELAUNCH_ENV_PROVENANCE` | <code>&quot;{\&quot;dotEnv\&quot;:[],\&quot;settingsEnv\&quot;:[]}&quot;</code> |
| `QWEN_CODE_PROJECT_DIR` | <code>&quot;/tmp/.qwen/projects/-work&quot;</code> |
| `QWEN_CODE_PROMPT_ID` | <code>&quot;a55d5088-cfb1-4d65-a8c9-070fd92108cb########0&quot;</code> |
| `QWEN_CODE_SESSION_ID` | <code>&quot;a55d5088-cfb1-4d65-a8c9-070fd92108cb&quot;</code> |
| `QWEN_CODE_STARTUP_VERSION` | <code>&quot;0.24.4&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `TERM` | <code>&quot;xterm-256color&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |

## vtcode

| Variable | Value |
| --- | --- |
| `CARGO_TERM_COLOR` | <code>&quot;never&quot;</code> |
| `GIT_PAGER` | <code>&quot;cat&quot;</code> |
| `GIT_TERMINAL_PROMPT` | <code>&quot;0&quot;</code> |
| `HOME` | <code>&quot;/tmp&quot;</code> |
| `HOSTNAME` | <code>&quot;5c605f4ec48a&quot;</code> |
| `NODE_VERSION` | <code>&quot;24.21.0&quot;</code> |
| `NO_COLOR` | <code>&quot;1&quot;</code> |
| `OPENAI_API_KEY` | <code>&quot;not-a-secret&quot;</code> |
| `PAGER` | <code>&quot;cat&quot;</code> |
| `PATH` | <code>&quot;/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin&quot;</code> |
| `PWD` | <code>&quot;/work&quot;</code> |
| `PYTHONUNBUFFERED` | <code>&quot;1&quot;</code> |
| `SHELL` | <code>&quot;/bin/bash&quot;</code> |
| `SHLVL` | <code>&quot;0&quot;</code> |
| `VTCODE` | <code>&quot;1&quot;</code> |
| `VTCODE_TRUST_WORKSPACE` | <code>&quot;full-auto&quot;</code> |
| `WORKSPACE_DIR` | <code>&quot;/work&quot;</code> |
| `XDG_CACHE_HOME` | <code>&quot;/tmp/cache&quot;</code> |
| `XDG_CONFIG_HOME` | <code>&quot;/tmp/config&quot;</code> |
| `XDG_DATA_HOME` | <code>&quot;/tmp/data&quot;</code> |
| `XDG_STATE_HOME` | <code>&quot;/tmp/state&quot;</code> |
| `YARN_VERSION` | <code>&quot;1.22.22&quot;</code> |
| `_` | <code>&quot;/usr/local/bin/agent-probe&quot;</code> |
