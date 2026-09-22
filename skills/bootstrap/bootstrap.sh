#!/usr/bin/env bash
#
# bootstrap — bring a bare machine up to where these repos can be worked on.
#
# The cycle, in the order the dependencies actually run:
#
#   1. packages   git, python, gh, node, rsync, php — plus, on macOS, Firefox,
#                 Sublime Text and Sublime Merge, because everything there
#                 comes from Homebrew
#   2. claude     the Claude desktop app and the Claude Code CLI
#   3. identity   git user.name and user.email, before anything can be committed
#   4. keys       an ed25519 key for GitHub and a SECOND one for NearlyFreeSpeech
#   5. clone      every repo in the suite, over SSH, into $MIND_DIR
#   6. deploy     the site repo's gitignored deploy.conf, from the NFSN login
#   7. hook       the brevity Stop hook, installed globally (see ../../AGENTS.md)
#   8. verify     prove each of the above rather than assume it
#
# TWO STEPS NEED A HUMAN and cannot be automated from here: a public key has to
# be pasted into github.com/settings/ssh/new, and another into the NFSN member
# panel. The script stops at each with the key on the clipboard and the URL on
# screen, and is written to be RE-RUN — every step checks for its own result
# first, so the second run picks up where the human left off and redoes nothing.
#
# Usage:
#   ./bootstrap.sh                 every step, in order, stopping at the gates
#   ./bootstrap.sh keys clone      only these steps, in the order given
#   ./bootstrap.sh --list          the step names and what each one does
#   ./bootstrap.sh -n              dry run: say what would happen, change nothing
#
# WHO THIS IS FOR IS NOT IN THIS FILE. This repo is public, so the name, the
# address, the GitHub account, the deploy login and the list of repos — one of
# which is private, and whose NAME is a disclosure on its own — all live in a
# config OUTSIDE it:
#
#   ~/.config/agentsuite/bootstrap.conf     (see bootstrap.conf.sample)
#
# Anything in there can also come from the environment, which is what CI and a
# one-off run should use. The script asks for whatever is missing and never
# guesses — a wrong address on a commit or a wrong host on a deploy is worse
# than a prompt.
set -euo pipefail

CONF="${BOOTSTRAP_CONF:-${XDG_CONFIG_HOME:-$HOME/.config}/agentsuite/bootstrap.conf}"
# Environment wins over the file: the file is the machine's standing answer,
# the environment is this run's.
[ -f "$CONF" ] && . "$CONF"

MIND_DIR="${MIND_DIR:-$HOME/GIT}"
GIT_NAME="${GIT_NAME:-}"
GIT_EMAIL="${GIT_EMAIL:-}"
GH_OWNER="${GH_OWNER:-}"
# Empty means ASK GITHUB: every non-fork repo the owner has. That is also why
# no list is written down here — a hardcoded one would have to name the private
# repos, and a repo name is the one part of a private repo that leaks.
REPOS="${REPOS:-}"
# Which checkout carries the deploy.conf that its deploy.sh needs.
SITE_REPO="${SITE_REPO:-}"
GH_KEY="$HOME/.ssh/id_ed25519"
NFSN_KEY="$HOME/.ssh/id_nfsn"
DRY=0


say()  { printf '==> %s\n' "$*"; }

# Ask once, then WRITE IT DOWN, so the next run and the next machine-wide step
# do not ask again. The file is chmod 600 under ~/.config and is not in any
# repo — see the header.
need() {
  local var="$1" prompt="$2" val
  eval "val=\${$var:-}"
  if [ -z "$val" ]; then
    [ -t 0 ] || { warn "$var is not set and there is no terminal to ask on — set it in $CONF"; return 1; }
    printf '    %s: ' "$prompt" >&2
    read -r val
    [ -n "$val" ] || { warn "$var is still empty"; return 1; }
    mkdir -p "$(dirname "$CONF")"; touch "$CONF"; chmod 600 "$CONF"
    printf '%s=%s\n' "$var" "$(printf '%s' "$val" | sed "s/'/'\\\\''/g; s/^/'/; s/\$/'/")" >> "$CONF"
    eval "$var=\$val"
  fi
}
warn() { printf '    ! %s\n' "$*" >&2; }
run()  { if [ "$DRY" = 1 ]; then printf '    would: %s\n' "$*"; else eval "$@"; fi; }

# A human gate: print the key, put it on the clipboard where there is one, and
# stop. Exit 10 rather than 1 — "waiting for you" is not "broken", and a caller
# driving this script can tell the two apart.
gate() {
  printf '\n'
  printf '  ┌─ needs you ─────────────────────────────────────────────\n'
  printf '  │ %s\n' "$1"
  printf '  │\n'
  printf '  │ %s\n' "$2"
  printf '  │\n'
  printf '  │ %s\n' "$3"
  printf '  └─────────────────────────────────────────────────────────\n'
  printf '\n  Then re-run: %s %s\n\n' "$0" "${STEP:-}"
  exit 10
}

clip() { command -v pbcopy >/dev/null 2>&1 && pbcopy < "$1" && echo "    (copied to the clipboard)"; true; }

# ---------------------------------------------------------------- the platform
PM=""
detect_pm() {
  if command -v brew    >/dev/null 2>&1; then PM=brew
  elif command -v pacman >/dev/null 2>&1; then PM=pacman
  elif command -v apt-get >/dev/null 2>&1; then PM=apt
  elif command -v dnf    >/dev/null 2>&1; then PM=dnf
  elif [ "$(uname -s)" = "Darwin" ]; then PM=brew-missing
  else PM=unknown
  fi
}

# Two checks, and both of them had to be argued with before they told the truth.
#
# 1. ANSWERED BY WHAT THE HOST SAYS, never by what ssh exits with. `ssh -T
#    git@github.com` authenticates and then exits 1, because there is no shell
#    to give you — and under `set -o pipefail` that 1 becomes the whole
#    pipeline's status however the grep went. So: captured, never piped.
#
# 2. THE KEY ON DISK, not whatever the agent happens to hold. On a machine that
#    already had an authorised key in the macOS keychain agent, a brand-new
#    unauthorised key tested as working — the agent answered for it, so the gate
#    said "done" about a key GitHub had never seen. `IdentityAgent=none` plus
#    `IdentitiesOnly=yes` and an explicit `-i` is what makes the question be
#    about the file this script just wrote. Both found on 2026-09-21 by running
#    the gate against a key that was supposed to fail, and watching it pass.
#
#    `-F /dev/null` is what finally made it honest, and it is worth knowing why
#    the other two were not enough. macOS's ssh resolves ~/.ssh/config from the
#    passwd entry, not from $HOME — so a test run under a throwaway HOME still
#    read the real config, found the real IdentityFile, and pulled the real key
#    out of the login Keychain (which `UseKeychain yes` asks for, and which
#    IdentitiesOnly does not restrain). Reading NO user config is the only form
#    of the question that is about the key file and nothing else.
KEYTEST="-F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityAgent=none -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"

github_ok() {
  case "$(ssh -T $KEYTEST -i "$GH_KEY" git@github.com 2>&1 || true)" in
    *"successfully authenticated"*) return 0 ;;
    *) return 1 ;;
  esac
}

nfsn_ok() {
  [ -n "${SUITE_DEPLOY_HOST:-}" ] || return 1
  ssh $KEYTEST -i "$NFSN_KEY" "$SUITE_DEPLOY_HOST" true 2>/dev/null
}

# ---------------------------------------------------------------- ARCH: A STUB
# UNRUN. There is no Arch machine here — this is macOS, and every line below is
# read off the dotfiles repo rather than off a working install, so treat it as
# the list to TRY and expect to fix a name or two the first time it meets a
# real box. It is written down because the alternative is rediscovering it, and
# the packages are not guesses: each one is something a config in the dotfiles
# repo actually invokes.
#
#   i3 config          picom, dex, xss-lock, i3lock, nm-applet, scrot, xclip
#   xinitrc/xprofile   startxfce4, dbus, xrandr, xrdb, feh
#   polybar, rofi      themselves, and a Nerd Font for their glyphs
#   kitty              $TERMINAL
#   openbox/rc.xml     openbox — a second WM, kept because the config is there
#
# THE AUDIO IS DELIBERATELY ABSENT — Sean, 2026-09-21: "the audio is broken in
# my config, so drop that". So no pulseaudio and no pavucontrol here, and the
# pieces in the dotfiles that drive them (polybar's pulseaudio module, the
# pactl binds in i3 and xbindkeysrc, the afix alias in bashrc) are the ones to
# leave behind when these are laid down. Installing a sound stack to match a
# config that does not work is how a broken setup gets reproduced faithfully.
arch_desktop() {
  run "sudo pacman -S --needed --noconfirm \
        i3-wm i3lock polybar rofi picom kitty \
        xfce4-session thunar xfce4-screenshooter openbox \
        xorg-server xorg-xinit xorg-xrandr xorg-xrdb \
        feh xbindkeys dex xss-lock network-manager-applet scrot xclip neofetch \
        ttf-firacode-nerd"
  # THE DOTFILES THEMSELVES: stow, because it is the existing solution and it
  # is one package — the repo's dotfiles/ tree becomes a stow package per
  # program and `stow -t ~` symlinks it, so an edit in the checkout is live and
  # `stow -D` backs it out. Left as a printed instruction rather than a run:
  # the repo is not laid out as stow packages yet, and a script that half-moves
  # someone's ~/.config on a machine nobody is watching is worse than a line of
  # text telling them what to do.
  cat <<'TXT'
    dotfiles: not laid down by this script yet.
      The existing solution is stow, one package per program:
        stow -d <dotfiles-repo> -t "$HOME" i3 polybar rofi picom kitty bash x
      That needs the repo restructured into those packages first, and it wants
      doing on the Arch box, not from here. Leave the audio pieces out.
TXT
}

# ---------------------------------------------------------------- ARCH: END

# brew's openjdk is KEG-ONLY: installed, working, and not on PATH — `java`
# resolves to the macOS stub that offers to send you to java.com, and gradle
# fails for want of a JDK that is sitting right there. The documented cure is a
# symlink into /Library/Java, which wants sudo; JAVA_HOME in the profile does
# not, so that is what this writes — between markers, so a re-run rewrites its
# own lines and leaves the rest of the profile alone.
jdk_on_path() {
  local jdk="$(brew --prefix)/opt/openjdk" rc begin="# >>> AgentSuite bootstrap (jdk) >>>"
  [ -x "$jdk/bin/java" ] || return 0
  for rc in "$HOME/.zshrc" "$HOME/.bash_profile"; do
    [ -f "$rc" ] || [ "$rc" = "$HOME/.zshrc" ] || continue
    grep -qF "$begin" "$rc" 2>/dev/null && continue
    if [ "$DRY" = 1 ]; then printf '    would: add JAVA_HOME to %s\n' "$rc"; continue; fi
    {
      printf '\n%s\n' "$begin"
      printf 'export JAVA_HOME="%s"\n' "$jdk"
      printf 'export PATH="$JAVA_HOME/bin:$PATH"\n'
      printf '# <<< AgentSuite bootstrap (jdk) <<<\n'
    } >> "$rc"
    echo "    JAVA_HOME -> $jdk (in $(basename "$rc"))"
  done
}

# ------------------------------------------------------------- 1. the packages
step_packages() {
  say "packages ($PM)"
  case "$PM" in
    brew-missing)
      # Homebrew is the package manager on macOS; without it there is nothing
      # to install into. Its installer is interactive (it asks for sudo), so it
      # is a gate rather than something to run unattended from here.
      gate "macOS with no Homebrew." \
           "Install it:  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"" \
           "It asks for your password — that is why this script does not run it for you." ;;
    brew)
      # EVERYTHING through Homebrew on macOS, formulae and casks alike — Sean,
      # 2026-09-21. A machine where half the tools came from a downloaded .dmg
      # has no one command that says what is installed or updates it, and the
      # half that was hand-installed is the half that silently goes stale.
      run "brew install git python gh node rsync php"
      # rust and cocoapods are not for writing anything here — they are what
      # the SUITE'S BUILDS need. The desktop bundle every Mind app ships is
      # Tauri, so `npm run build` in desktop/ is a cargo build wearing a
      # different name, and the iOS prebuild wants pods. Both were missing on
      # 2026-09-21 and each was found one failed build at a time, which is the
      # thing this script exists to stop.
      run "brew install rust cocoapods watchman jq openjdk gradle"
      # The Android side: platform-tools give adb, which is what "install it
      # on the emulator" means. NOT the temurin cask — its installer wants a
      # sudo password, so it cannot run unattended and it failed exactly that
      # way on 2026-09-21; brew's own openjdk above is the same JDK without
      # the prompt.
      run "brew install --cask android-platform-tools"
      jdk_on_path
      # The apps. Casks auto-update themselves, so this is a one-time install
      # and re-running it is a no-op rather than a reinstall.
      run "brew install --cask firefox sublime-text sublime-merge rectangle" ;;
    pacman)
      # THE TOOLCHAIN, same job as the brew block above.
      run "sudo pacman -S --needed --noconfirm git python python-pip github-cli nodejs npm rsync php rust jq stow firefox"
      arch_desktop ;;
    apt)
      run "sudo apt-get update"
      # gh is not in Debian/Ubuntu's own archive; its repo has to be added
      # first, so the base set installs either way and gh is handled after.
      run "sudo apt-get install -y git python3 python3-pip nodejs npm rsync php-cli curl"
      if ! command -v gh >/dev/null 2>&1; then
        run "sudo mkdir -p -m 755 /etc/apt/keyrings"
        run "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null"
        run "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg"
        run "echo 'deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null"
        run "sudo apt-get update && sudo apt-get install -y gh"
      fi ;;
    dnf)
      run "sudo dnf install -y git python3 gh nodejs npm rsync php-cli" ;;
    *)
      warn "no package manager I know — install git, python, gh, node, rsync and php by hand"; return 1 ;;
  esac
}

# --------------------------------------------------------------- 2. the Claude
step_claude() {
  say "claude"
  if [ "$PM" = brew ]; then
    # Two separate things with similar names: `claude` is the desktop app,
    # `claude-code` is the terminal agent these repos are actually worked on
    # with. Both are casks; both auto-update, so this is a one-time install.
    run "brew install --cask claude claude-code"
  else
    # No cask outside macOS. The official installer puts the CLI in ~/.local/bin
    # and is the supported path on Linux; the desktop app is macOS/Windows only.
    if command -v claude >/dev/null 2>&1; then
      echo "    claude code is already here: $(command -v claude)"
    else
      run "curl -fsSL https://claude.ai/install.sh | bash"
    fi
    warn "the Claude desktop app is macOS/Windows only — this machine gets the CLI"
  fi
}

# ------------------------------------------------------------- 3. the identity
# Before the keys, because the keys are labelled with the same address — and
# well before the first commit, since git refuses one without an identity and
# the machine that has just been bootstrapped is exactly the one that has none.
step_identity() {
  say "identity"
  need GIT_NAME  "your name, as it should read on a commit" || return 1
  need GIT_EMAIL "the address for commits (GitHub's noreply one keeps it off a scraper)" || return 1
  local have_n have_e
  have_n="$(git config --global user.name  2>/dev/null || true)"
  have_e="$(git config --global user.email 2>/dev/null || true)"
  if [ "$have_n" != "$GIT_NAME" ]; then
    [ -n "$have_n" ] && warn "user.name was '$have_n'"
    run "git config --global user.name '$GIT_NAME'"
  fi
  if [ "$have_e" != "$GIT_EMAIL" ]; then
    [ -n "$have_e" ] && warn "user.email was '$have_e'"
    run "git config --global user.email '$GIT_EMAIL'"
  fi
  echo "    $GIT_NAME <$GIT_EMAIL>"
}

# ----------------------------------------------------------------- 4. the keys
# TWO keys, not one. The same key would work for both hosts, but a key is the
# unit you revoke: a laptop that loses GitHub access should not also lose the
# ability to deploy, and vice versa. They are told apart by ~/.ssh/config.
step_keys() {
  say "keys"
  mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
  # Labelled with the commit identity and the machine, so the list on GitHub's
  # settings page says which laptop a key is, which is what you need when the
  # reason you are reading that list is to revoke one of them.
  local label="$GIT_EMAIL $(hostname -s)"

  [ -f "$GH_KEY" ]   || run "ssh-keygen -t ed25519 -C '$label' -f '$GH_KEY' -N '' -q"
  [ -f "$NFSN_KEY" ] || run "ssh-keygen -t ed25519 -C '$label (nfsn)' -f '$NFSN_KEY' -N '' -q"

  # ~/.ssh/config, between markers so a re-run rewrites its own block and
  # leaves every other Host the machine has alone.
  local cfg="$HOME/.ssh/config" begin="# >>> AgentSuite bootstrap >>>" end="# <<< AgentSuite bootstrap <<<"
  if ! grep -qF "$begin" "$cfg" 2>/dev/null; then
    say "  writing the Host blocks into ~/.ssh/config"
    if [ "$DRY" = 0 ]; then
      { [ -f "$cfg" ] && cat "$cfg"; cat <<CFG
$begin
Host github.com
  HostName github.com
  User git
  IdentityFile $GH_KEY
  IdentitiesOnly yes
  AddKeysToAgent yes
$([ "$(uname -s)" = Darwin ] && echo '  UseKeychain yes')

# The deploy target. HostName is filled in by the 'deploy' step, which is where
# the realm is known; until then this block documents which key goes where.
Host *.nearlyfreespeech.net
  IdentityFile $NFSN_KEY
  IdentitiesOnly yes
  AddKeysToAgent yes
$([ "$(uname -s)" = Darwin ] && echo '  UseKeychain yes')
$end
CFG
      } > "$cfg.new" && mv "$cfg.new" "$cfg" && chmod 600 "$cfg"
    fi
  fi

  if [ "$(uname -s)" = Darwin ]; then
    run "ssh-add --apple-use-keychain '$GH_KEY' '$NFSN_KEY' >/dev/null 2>&1 || true"
  else
    run "ssh-add '$GH_KEY' '$NFSN_KEY' >/dev/null 2>&1 || true"
  fi
  [ "$DRY" = 1 ] && return 0

  # The gates. Each is skipped once its host answers, which is what makes the
  # re-run cheap: authorise one key, run again, and it walks straight to the next.
  # NOT a pipeline. `ssh -T git@github.com` exits 1 even when it authenticates
  # — GitHub refuses the shell — and under `set -o pipefail` that 1 is the whole
  # pipeline's status however the grep went, so a piped check reads a working
  # key as a broken one and gates forever. Caught on 2026-09-21 by running it.
  if ! github_ok; then
    clip "$GH_KEY.pub"; cat "$GH_KEY.pub"
    STEP=keys gate "GitHub does not know this key yet." \
         "Paste it at  https://github.com/settings/ssh/new" \
         "Title it after the machine — the key is what you revoke when you lose it."
  fi
  echo "    github: authenticated"

  if [ -z "${SUITE_DEPLOY_HOST:-}" ]; then
    warn "no SUITE_DEPLOY_HOST — the NFSN key is made but untested; set it and re-run"
    return 0
  fi
  if ! nfsn_ok; then
    clip "$NFSN_KEY.pub"; cat "$NFSN_KEY.pub"
    STEP=keys gate "NearlyFreeSpeech does not know this key yet." \
         "Paste it in the member panel: Profile -> Add SSH Key (it may read 'Manage SSH Keys')." \
         "It is a PROFILE key, not a per-site one, and it can take a minute to take effect."
  fi
  echo "    nfsn: authenticated"
}

# --------------------------------------------------------------- 5. the clones
step_clone() {
  need GH_OWNER "the GitHub account the repos belong to" || return 1
  # No list configured: ask GitHub for one. Private repos come along because gh
  # is authenticated as their owner, and none of their names had to be written
  # down anywhere to get them.
  if [ -z "$REPOS" ]; then
    command -v gh >/dev/null 2>&1 || { warn "no REPOS set and no gh to ask — set REPOS in $CONF"; return 1; }
    gh auth status >/dev/null 2>&1 || { warn "gh is not logged in: run  gh auth login  (private repos need it)"; return 1; }
    REPOS="$(gh repo list "$GH_OWNER" --limit 200 --no-archived --source --json name --jq '.[].name' | tr '\n' ' ')"
    [ -n "$REPOS" ] || { warn "gh returned no repos for $GH_OWNER"; return 1; }
  fi
  say "clone -> $MIND_DIR"
  run "mkdir -p '$MIND_DIR'"
  for r in $REPOS; do
    if [ -d "$MIND_DIR/$r/.git" ]; then
      # Already here: pull rather than re-clone, and --autostash because two
      # sessions share these trees (../../AGENTS.md, Git).
      run "git -C '$MIND_DIR/$r' pull --autostash --quiet" || warn "$r: pull failed"
      echo "    $r: up to date"
    else
      # SSH, not HTTPS. The private repos in this list are unreachable over
      # HTTPS without a token, and a tree cloned over HTTPS cannot push without
      # one either — so the key from step 3 is the thing that makes this work.
      run "git clone --quiet 'git@github.com:$GH_OWNER/$r.git' '$MIND_DIR/$r'" || warn "$r: clone failed"
      echo "    $r: cloned"
    fi
  done
}

# --------------------------------------------------------------- 6. the deploy
step_deploy() {
  say "deploy.conf"
  need SITE_REPO "the repo whose deploy.sh needs a deploy.conf" || return 1
  local site="$MIND_DIR/$SITE_REPO"
  [ -d "$site" ] || { warn "no $site yet — run the clone step first"; return 0; }
  [ -f "$site/deploy.sh" ] || { warn "$SITE_REPO has no deploy.sh — nothing to configure"; return 0; }
  if [ -f "$site/deploy.conf" ]; then echo "    already written"; return 0; fi
  if [ -z "${SUITE_DEPLOY_HOST:-}" ]; then
    STEP=deploy gate "deploy.sh has no target, and deploy.conf is gitignored so no clone carries one." \
         "Set it:  export SUITE_DEPLOY_HOST=<sshuser>_<site>@ssh.<realm>.nearlyfreespeech.net" \
         "Both halves are on the NFSN panel's Site Information page."
  fi
  run "printf 'HOST=\"%s\"\n' '$SUITE_DEPLOY_HOST' > '$site/deploy.conf'"
  echo "    written (gitignored, stays on this machine)"
}

# ----------------------------------------------------------------- 7. the hook
# ../../AGENTS.md: brevity is enforced by a Stop hook rather than trusted to
# prose, and it is installed once globally rather than per repo.
step_hook() {
  say "brevity hook"
  local src="$(cd "$(dirname "$0")/../.." && pwd)/hooks/brevity.py"
  [ -f "$src" ] || { warn "no hooks/brevity.py beside this script"; return 0; }
  run "mkdir -p '$HOME/.claude/hooks'"
  run "cp '$src' '$HOME/.claude/hooks/brevity.py'"
  [ "$DRY" = 1 ] && return 0
  # Merged, never overwritten: ~/.claude/settings.json holds everything else
  # about this machine's Claude Code, and a bootstrap that clobbered it would
  # cost more than it saved. Idempotent — the same hook is not added twice.
  python3 - "$HOME/.claude/settings.json" <<'PY'
import json, os, sys
p = sys.argv[1]
s = {}
if os.path.exists(p):
    with open(p) as f:
        try: s = json.load(f)
        except ValueError:
            sys.exit("settings.json is not valid JSON — left alone, add the Stop hook by hand")
cmd = "python3 $HOME/.claude/hooks/brevity.py"
stop = s.setdefault("hooks", {}).setdefault("Stop", [])
if not any(h.get("command") == cmd for m in stop for h in m.get("hooks", [])):
    stop.append({"matcher": "", "hooks": [{"type": "command", "command": cmd}]})
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: json.dump(s, f, indent=2)
    print("    Stop hook added to ~/.claude/settings.json")
else:
    print("    Stop hook already installed")
PY
}

# ---------------------------------------------------------------- 8. the proof
# ../../AGENTS.md, Tests: a green check nobody watched fail proves nothing. So
# this step runs the real things — a real auth, a real lint, the real suite —
# rather than checking that a file exists.
step_verify() {
  say "verify"
  local bad=0
  for c in git python3 gh node rsync php claude cargo pod adb jq; do
    if command -v "$c" >/dev/null 2>&1; then printf '    %-8s %s\n' "$c" "$(command -v "$c")"
    else printf '    %-8s MISSING\n' "$c"; bad=1; fi
  done
  github_ok && echo "    github   authenticated" || { echo "    github   NOT authenticated"; bad=1; }
  if [ -n "${SUITE_DEPLOY_HOST:-}" ]; then
    nfsn_ok && echo "    nfsn     authenticated" || { echo "    nfsn     NOT authenticated"; bad=1; }
  fi
  for r in $REPOS; do [ -d "$MIND_DIR/$r/.git" ] || { echo "    $r MISSING"; bad=1; }; done
  [ -n "$REPOS" ] || echo "    repos    not listed here (asked of gh at clone time)"
  if [ -n "$SITE_REPO" ] && [ -f "$MIND_DIR/$SITE_REPO/tools/test.php" ] && command -v php >/dev/null 2>&1; then
    ( cd "$MIND_DIR/$SITE_REPO" && php tools/test.php >/tmp/bootstrap-test.$$ 2>&1 \
      && echo "    site     $(tail -1 /tmp/bootstrap-test.$$)" \
      || { echo "    site     TESTS FAILED — see /tmp/bootstrap-test.$$"; bad=1; } )
  fi
  [ "$bad" = 0 ] && say "ready" || { warn "not ready — see the lines above"; return 1; }
}

# ------------------------------------------------------------------ the driver
STEPS="packages claude identity keys clone deploy hook verify"
usage() {
  cat <<TXT
bootstrap — bring a bare machine up to where these repos can be worked on.

  packages   git, python, gh, node, rsync, php — and on macOS the apps too:
             firefox, sublime-text, sublime-merge (everything via Homebrew)
  claude     the Claude desktop app and the Claude Code CLI
  identity   git user.name and user.email, from ~/.config/agentsuite/bootstrap.conf
  keys       an ed25519 key for GitHub and a second one for NearlyFreeSpeech
  clone      every repo the account owns, over SSH, into \$MIND_DIR (${MIND_DIR})
  deploy     the site repo's gitignored deploy.conf
  hook       the brevity Stop hook, installed globally
  verify     prove all of the above

Usage: $0 [-n] [step ...]      no steps means all of them, in order
Exit:  0 done · 10 waiting on you (a key to paste) · 1 something failed
TXT
}

WANT=""
for a in "$@"; do
  case "$a" in
    -n|--dry-run) DRY=1 ;;
    -l|--list|-h|--help) usage; exit 0 ;;
    *) case " $STEPS " in *" $a "*) WANT="$WANT $a" ;;
         *) echo "unknown step: $a" >&2; usage >&2; exit 1 ;; esac ;;
  esac
done
WANT="${WANT:-$STEPS}"

detect_pm
[ "$DRY" = 1 ] && say "DRY RUN — nothing will change"
for s in $WANT; do STEP="$s"; "step_$s"; done
