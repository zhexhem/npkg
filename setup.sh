#!/usr/bin/env bash
# =============================================================================
# npkg setup script — see --help
# =============================================================================
set -euo pipefail

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_INFO=$'\033[38;2;137;180;250m'; C_OK=$'\033[38;2;166;227;161m'
  C_WARN=$'\033[38;2;249;226;175m'; C_ERR=$'\033[38;2;243;139;168m'
  C_ACCENT=$'\033[38;2;203;166;247m'
else
  C_RESET=; C_BOLD=; C_DIM=; C_INFO=; C_OK=; C_WARN=; C_ERR=; C_ACCENT=
fi

log()  { printf '%s•%s %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_OK"   "$C_RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$C_WARN" "$C_RESET" "$*" >&2; }
err()  { printf '%s✗%s %s\n' "$C_ERR"  "$C_RESET" "$*" >&2; }
die()  { err "$*"; exit 1; }
hr()   { printf '%s%s%s\n' "$C_DIM" "──────────────────────────────────────────────────────────────" "$C_RESET"; }

banner() {
  local text="$1"
  local line; line="$(printf '─%.0s' $(seq 1 $(( ${#text} + 4 ))))"
  printf '%s╭%s╮%s\n' "$C_ACCENT" "$line" "$C_RESET"
  printf '%s│%s %s%s%s %s│%s\n' "$C_ACCENT" "$C_RESET" "$C_BOLD" "$text" "$C_RESET" "$C_ACCENT" "$C_RESET"
  printf '%s╰%s╯%s\n' "$C_ACCENT" "$line" "$C_RESET"
}

MODE="venv"; WITH_DEV=0; WIRE=1; WIRE_MODE="append"; UNINSTALL=0
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

NPKG_CONFIG_DIR="${NPKG_CONFIG_DIR:-$HOME/.config/nvim/npkg}"
NPKG_DATA_DIR="${NPKG_DATA_DIR:-$HOME/.local/share/nvim/npkg}"
NPKG_PLUGIN_DIR="${NPKG_PLUGIN_DIR:-$NPKG_DATA_DIR/plugins}"
NPKG_RUNTIME_FILE="${NPKG_RUNTIME_FILE:-$NPKG_CONFIG_DIR/runtime.lua}"
NPKG_VENV="$NPKG_CONFIG_DIR/venv"
NVIM_CONFIG_DIR="${NVIM_CONFIG_DIR:-$HOME/.config/nvim}"
NVIM_INIT_LUA="$NVIM_CONFIG_DIR/init.lua"

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)         MODE="${2:?}"; shift 2 ;;
    --mode=*)       MODE="${1#*=}"; shift ;;
    --dev)          WITH_DEV=1; shift ;;
    --no-wire)      WIRE=0; shift ;;
    --wire-mode)    WIRE_MODE="${2:?}"; shift 2 ;;
    --wire-mode=*)  WIRE_MODE="${1#*=}"; shift ;;
    --uninstall)    UNINSTALL=1; shift ;;
    -h|--help)      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)              die "Unknown option: $1" ;;
  esac
done
case "$MODE" in venv|pipx|system) ;; *) die "Invalid --mode: $MODE" ;; esac

if [ "$UNINSTALL" -eq 1 ]; then
  banner "npkg uninstall"
  for d in "$NPKG_VENV" "$NPKG_PLUGIN_DIR"; do
    [ -e "$d" ] && { log "Removing $d"; rm -rf "$d"; }
  done
  for f in "$NPKG_RUNTIME_FILE" "$NPKG_CONFIG_DIR/lock.json"; do
    [ -e "$f" ] && rm -f "$f"
  done
  if command -v pipx >/dev/null 2>&1; then pipx uninstall npkg 2>/dev/null || true; fi
  ok "Uninstall complete."
  exit 0
fi

banner "npkg setup"; echo
log "Detecting Python interpreter…"
PYTHON=""
for cand in python3.12 python3.11 python3.10 python3.9 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
      PYTHON="$(command -v "$cand")"; break
    fi
  fi
done
[ -n "$PYTHON" ] || die "No Python ≥3.9 found in PATH."
ok "Using $PYTHON ($("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'))"

SRC=""
if [ -f "$SCRIPT_DIR/pyproject.toml" ] && [ -d "$SCRIPT_DIR/npkg" ]; then
  SRC="$SCRIPT_DIR"; ok "Source: $SRC"
elif [ -f "$SCRIPT_DIR/setup.py" ] && [ -f "$SCRIPT_DIR/manager.py" ]; then
  SRC="$SCRIPT_DIR"; ok "Single-file source: $SRC"
else
  warn "No local source; assuming npkg on PATH."
fi

mkdir -p "$NPKG_CONFIG_DIR" "$NPKG_DATA_DIR" "$NPKG_PLUGIN_DIR"
ok "config:  $NPKG_CONFIG_DIR"
ok "data:    $NPKG_DATA_DIR"
ok "plugins: $NPKG_PLUGIN_DIR"

case "$MODE" in
  venv)
    log "Creating venv at $NPKG_VENV"
    "$PYTHON" -m venv "$NPKG_VENV"
    # shellcheck disable=SC1091
    source "$NPKG_VENV/bin/activate"
    python -m pip install --quiet --upgrade pip wheel setuptools
    if [ -n "$SRC" ]; then
      [ "$WITH_DEV" -eq 1 ] && python -m pip install --quiet -e "$SRC[dev]" \
                            || python -m pip install --quiet -e "$SRC"
    else
      python -m pip install --quiet npkg
    fi
    ok "venv install complete."
    ;;
  pipx)
    command -v pipx >/dev/null 2>&1 || die "pipx not found."
    [ -n "$SRC" ] && pipx install --force "$SRC" || pipx install npkg
    ok "pipx install complete."
    ;;
  system)
    [ -n "$SRC" ] && "$PYTHON" -m pip install --quiet --user -e "$SRC" \
                  || "$PYTHON" -m pip install --quiet --user npkg
    ok "system install complete."
    ;;
esac

case "$MODE" in
  venv) NPKG_CMD="$NPKG_VENV/bin/npkg" ;;
  *)    NPKG_CMD="$(command -v npkg || echo "python -m npkg")" ;;
esac

log "Verifying…"
eval "$NPKG_CMD --version" >/dev/null 2>&1 && ok "$(eval "$NPKG_CMD --version")" \
  || die "Verification failed."

if [ ! -f "$NPKG_CONFIG_DIR/plugins.json" ]; then
  log "Writing starter plugins.json…"
  cat > "$NPKG_CONFIG_DIR/plugins.json" <<JSON
{
  "settings": { "theme": "tokyo" },
  "plugins": {
    "vim-stylus":      { "repo": "wavded/vim-stylus" },
    "nvim-treesitter": { "repo": "nvim-treesitter/nvim-treesitter",
                         "branch": "master", "build": "TSUpdate" },
    "plenary.nvim":    { "repo": "nvim-lua/plenary.nvim" },
    "telescope.nvim":  { "repo": "nvim-telescope/telescope.nvim",
                         "dependencies": ["plenary.nvim"] }
  }
}
JSON
  ok "Created $NPKG_CONFIG_DIR/plugins.json"
fi

if [ "$WIRE" -eq 1 ] && [ "$WIRE_MODE" != "none" ]; then
  mkdir -p "$NVIM_CONFIG_DIR"
  NPKG_LUA_BLOCK="$(cat <<LUA
-- >>> npkg (auto-generated by setup.sh) >>>
local npkg_runtime = "${NPKG_RUNTIME_FILE}"
if vim.fn.filereadable(npkg_runtime) == 1 then dofile(npkg_runtime) end

local function npkg(args)
  local parts = { "NVIM=" .. vim.v.servername, "npkg",
                  "--config-dir=${NPKG_CONFIG_DIR}",
                  "--data-dir=${NPKG_DATA_DIR}",
                  "--plugin-dir=${NPKG_PLUGIN_DIR}",
                  "--runtime-file=${NPKG_RUNTIME_FILE}" }
  parts[#parts + 1] = args
  vim.cmd("!" .. table.concat(parts, " "))
  if vim.fn.filereadable(npkg_runtime) == 1 then dofile(npkg_runtime) end
end

vim.api.nvim_create_user_command("NpkgInstall",
  function(o) npkg("install " .. (o.args ~= "" and "--plugin " .. o.args or "")) end, { nargs = "?" })
vim.api.nvim_create_user_command("NpkgUpdate",
  function(o) npkg("update " .. (o.args ~= "" and "--plugin " .. o.args or "")) end, { nargs = "?" })
vim.api.nvim_create_user_command("NpkgClean",  function() npkg("clean")  end, {})
vim.api.nvim_create_user_command("NpkgList",   function() npkg("list")   end, {})
vim.api.nvim_create_user_command("NpkgSync",   function() npkg("sync")   end, {})
vim.api.nvim_create_user_command("NpkgThemes", function() npkg("themes") end, {})
vim.api.nvim_create_user_command("NpkgPaths",  function() npkg("paths")  end, {})
-- <<< npkg <<<
LUA
)"

  if [ ! -f "$NVIM_INIT_LUA" ]; then
    printf '%s\n' "$NPKG_LUA_BLOCK" > "$NVIM_INIT_LUA"
    ok "Wrote $NVIM_INIT_LUA"
  elif grep -q '>>> npkg (auto-generated' "$NVIM_INIT_LUA" 2>/dev/null; then
    warn "npkg block already present in $NVIM_INIT_LUA"
  elif [ "$WIRE_MODE" = "append" ]; then
    printf '\n%s\n' "$NPKG_LUA_BLOCK" >> "$NVIM_INIT_LUA"
    ok "Appended npkg block to $NVIM_INIT_LUA"
  elif [ "$WIRE_MODE" = "write" ]; then
    warn "OVERWRITE $NVIM_INIT_LUA?"
    read -r -p "Continue? [y/N] " ans
    if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
      cp "$NVIM_INIT_LUA" "$NVIM_INIT_LUA.bak.$(date +%s)"
      printf '%s\n' "$NPKG_LUA_BLOCK" > "$NVIM_INIT_LUA"
      ok "Wrote init.lua (backup saved)"
    fi
  fi
fi

echo; hr
ok "npkg is ready."
echo
printf '%sDirectories%s\n' "$C_BOLD" "$C_RESET"
printf '  %-10s %s\n' "config:"  "$NPKG_CONFIG_DIR"
printf '  %-10s %s\n' "data:"    "$NPKG_DATA_DIR"
printf '  %-10s %s\n' "plugins:" "$NPKG_PLUGIN_DIR"
printf '  %-10s %s\n' "runtime:" "$NPKG_RUNTIME_FILE"
echo
printf '%sNext%s\n' "$C_BOLD" "$C_RESET"
printf '  %s install          # install plugins\n' "$NPKG_CMD"
printf '  %s themes           # preview themes\n' "$NPKG_CMD"
printf '  :NpkgList           # inside Neovim\n'
hr