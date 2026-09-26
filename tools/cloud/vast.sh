#!/bin/zsh
# Cloud GPU jobs on Vast.ai for Clash of Ages (see PROGRESS.md session 13, and the `vast-ai` skill for the rules).
#
#   tools/cloud/vast.sh search [gpu]                  verified 1×RTX 4090 (default) or 3090 offers, ≥16 cores, cheapest first
#   tools/cloud/vast.sh up [offer_id]                 rent (4090 offers first, then 3090), wait for SSH, bootstrap Blender + both repos
#   tools/cloud/vast.sh run '<command>'               run a command in /work/repo on the box (streams output)
#   tools/cloud/vast.sh blender <script.py> [-- args] run a Blender script headless on the GPU (foreground; short jobs only)
#   tools/cloud/vast.sh batch <script.py> [-- args]   same, detached under nohup; prints the log path.  VAST_ENV="QUALITY=final" to pass env
#   tools/cloud/vast.sh wait [log]                    poll a batch log until "=== END rc=", printing progress; exits with that rc
#   tools/cloud/vast.sh log [n]                       tail the latest batch log
#   tools/cloud/vast.sh pull <repo-relative path>...  rsync results back into this checkout
#   tools/cloud/vast.sh push <repo-relative path>...  rsync local, uncommitted files up to the box
#   tools/cloud/vast.sh sync                          git fetch + reset the box's repo clone to origin/main
#   tools/cloud/vast.sh ssh                           interactive shell
#   tools/cloud/vast.sh status | down                 show / destroy OUR box (always `down` when finished)
#   tools/cloud/vast.sh list                          every instance on the account — other sessions' boxes appear here; never touch them
#   tools/cloud/vast.sh cost [start|end]              credit, every running box and its $/h; `start`/`end` bracket a session's spend
#
# One Vast account is shared by several Claude sessions (rules in ~/.claude/skills/vast-ai/SKILL.md):
#   * this tool ALWAYS names its box (VAST_NAME, default "coa") and `down` only ever destroys the id in its own state file;
#   * `list` is for counting and reporting — an instance that is not ours belongs to another session.
# Needs ~/.env with VAST_SESSION_KEY (from ~/.vast/login.sh <2FA code>), ~/.ssh/vast_ed25519 (registered on the Vast account)
# and the two read-only deploy keys ~/.ssh/coa_deploy_ed25519 (github.com/dhruvdesmond/coc-clone) and
# ~/.ssh/blenderlib_deploy_ed25519 (github.com/dhruvdesmond/blender-lib).
set -e
ROOT=${0:A:h:h:h}
VAST_NAME=${VAST_NAME:-coa}
STATE="$HOME/.vast/instance-$VAST_NAME"
LEDGER="$HOME/.vast/ledger-$VAST_NAME.csv"
API=https://console.vast.ai/api
KEY="$HOME/.ssh/vast_ed25519"
DEPLOY_REPO="$HOME/.ssh/coa_deploy_ed25519"
DEPLOY_LIB="$HOME/.ssh/blenderlib_deploy_ed25519"
REPO_URL=git@github.com:dhruvdesmond/coc-clone.git
LIB_URL=git@github.com:dhruvdesmond/blender-lib.git
BLENDER_URL=https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz
IMAGE=nvidia/cuda:12.4.1-runtime-ubuntu22.04
DISK=${VAST_DISK:-80}
set -a; . "$HOME/.env"; set +a
AUTH=(-H "Authorization: Bearer ${VAST_SESSION_KEY:-$VAST_API_KEY}")

py() { local c=$1; shift; python3 -c "$c" "$@"; }
api() { local m=$1 p=$2; shift 2; curl -s -m 60 -X $m "${AUTH[@]}" -H "Content-Type: application/json" "$API$p" "$@"; }
need_instance() { [[ -f $STATE ]] || { echo "no instance for '$VAST_NAME': run 'tools/cloud/vast.sh up' first"; exit 1; }; source $STATE; }
sshx() { need_instance; ssh -i $KEY -p $PORT -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o LogLevel=ERROR root@$HOST "$@"; }
credit() { api GET "/v0/users/current/" | py "import sys,json;print('%.3f' % (json.load(sys.stdin).get('credit') or 0))"; }
ledger() { mkdir -p ${LEDGER:h}; printf '%s,%s,%s,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "${2:--}" "$(credit)" >> $LEDGER; }

search() {  # $1 = gpu name (default RTX 4090)
  local gpu=${1:-RTX 4090}
  local q='{"gpu_name":{"eq":"'$gpu'"},"num_gpus":{"eq":1},"rentable":{"eq":true},"verified":{"eq":true},"reliability2":{"gte":0.98},"cpu_cores_effective":{"gte":16},"inet_down":{"gte":400},"disk_space":{"gte":'$DISK'},"cuda_max_good":{"gte":12.4},"order":[["dph_total","asc"]],"type":"on-demand"}'
  curl -s -m 30 "$API/v0/bundles/?q=$(py "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$q")" | py "
import sys,json
o=json.load(sys.stdin).get('offers',[])
for x in o[:8]:
    disk=(x.get('storage_cost') or 0)*$DISK/730.0
    print('%9d  %-9s \$%.3f/h +disk \$%.3f/h  rel %.3f  %2.0f cores  %3.0f GB RAM  down %4.0f Mbps  net \$%.4f/GB  %s' % (x['id'], x['gpu_name'], x['dph_total'], disk, x.get('reliability2',0), x.get('cpu_cores_effective',0), x.get('cpu_ram',0)/1024, x.get('inet_down',0), x.get('inet_down_cost') or 0, x.get('geolocation','')))
"
}

inst() {  # print "status host port msg" for instance $1 (Vast SSH proxy)
  api GET "/v0/instances/$1/" | py "
import sys,json
d=json.load(sys.stdin); v=d.get('instances',d)
v=v[0] if isinstance(v,list) and v else (v if isinstance(v,dict) else {})
msg=(v.get('status_msg') or '').replace(' ','_')[:60] or '-'
print(v.get('actual_status') or '-', v.get('ssh_host') or '-', v.get('ssh_port') or '-', msg)"
}

try_offer() {  # rent one offer; returns 0 once SSH is reachable, else destroys it
  local offer=$1
  echo "renting offer $offer…"
  local r=$(api PUT "/v0/asks/$offer/" -d "{\"client_id\":\"me\",\"image\":\"$IMAGE\",\"disk\":$DISK,\"runtype\":\"ssh\",\"label\":\"coa-$VAST_NAME\"}")
  local id=$(printf '%s' "$r" | py "import sys,json;d=json.load(sys.stdin);print(d.get('new_contract') or '')")
  [[ -n $id ]] || { echo "  rent failed: $(printf '%s' "$r" | head -c 160)"; return 1; }
  mkdir -p ${STATE:h}; echo "ID=$id" > $STATE
  local st host port msg
  for i in {1..60}; do                                    # up to ~10 min for the image pull
    read st host port msg <<< "$(inst $id)"
    # Only real host failures (e.g. "docker_build() error writing dockerfile", "Error response from daemon"),
    # not apt/pull progress lines that merely contain the word (e.g. liberror-perl).
    if [[ $st != running && ( $msg == Error* || $msg == *docker_build\(\)_error* || $msg == *daemon* ) ]]; then echo "  host error: $msg"; down; return 1; fi
    [[ $st == running && $host != - ]] && break
    (( i % 6 == 0 )) && echo "  …$st ${msg//_/ }"
    sleep 10
  done
  [[ $st == running ]] || { echo "  did not start ($st) — destroying"; down; return 1; }
  printf 'ID=%s\nHOST=%s\nPORT=%s\n' $id $host $port > $STATE
  for i in {1..60}; do sshx true 2>/dev/null && return 0; (( i % 12 == 0 )) && echo "  …waiting for SSH ($((i * 10)) s)"; sleep 10; done
  echo "  SSH never answered in 10 min — destroying"; down; return 1
}

up() {
  [[ -f $STATE ]] && { echo "instance already recorded in $STATE (run 'down' first)"; exit 1; }
  echo "credit before: \$$(credit)   other boxes on the account:"; list | sed 's/^/  /'
  local offers
  if [[ -n $1 ]]; then offers=($1); else offers=($(search "RTX 4090" | awk '{print $1}' | head -${VAST_TRY:-3}) $(search "RTX 3090" | awk '{print $1}' | head -2)); fi
  echo "offers to try: $offers"
  local ok=0
  for o in $offers; do try_offer $o && { ok=1; break; }; done
  (( ok )) || { echo "no offer came up"; exit 1; }
  source $STATE
  ledger up $ID
  echo "running (id $ID, $HOST:$PORT) — bootstrapping Blender + both repos"
  scp -i $KEY -P $PORT -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR $DEPLOY_REPO root@$HOST:/root/.ssh/deploy_repo >/dev/null
  scp -i $KEY -P $PORT -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR $DEPLOY_LIB root@$HOST:/root/.ssh/deploy_lib >/dev/null
  sshx "set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq && apt-get install -y -qq git rsync xz-utils curl libxrender1 libxi6 libxkbcommon0 libsm6 libgl1 libxfixes3 libxxf86vm1 libegl1 >/dev/null
    chmod 600 /root/.ssh/deploy_repo /root/.ssh/deploy_lib
    mkdir -p /work/logs /work/out && cd /work
    [ -d blender ] || { curl -sL $BLENDER_URL | tar xJ && mv blender-5.2.1-linux-x64 blender; }
    [ -d repo ] || GIT_SSH_COMMAND='ssh -i /root/.ssh/deploy_repo -o StrictHostKeyChecking=accept-new' git clone -q --depth 1 $REPO_URL repo
    [ -d blender-lib ] || GIT_SSH_COMMAND='ssh -i /root/.ssh/deploy_lib -o StrictHostKeyChecking=accept-new' git clone -q --depth 1 $LIB_URL blender-lib
    /work/blender/blender -b --factory-startup --python-expr 'import bpy; p=bpy.context.preferences.addons[\"cycles\"].preferences; p.compute_device_type=\"CUDA\"; p.get_devices(); print(\"GPU:\", [d.name for d in p.devices if d.type==\"CUDA\"])' 2>/dev/null | grep GPU:
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
    nproc; git -C /work/repo log --oneline -1; git -C /work/blender-lib log --oneline -1"
  echo "ready. billing is running — 'tools/cloud/vast.sh down' when finished"
}

# Blender 5.2's OptiX kernels need a newer NVIDIA driver than many hosts run (565 failed with
# OPTIX_ERROR_INTERNAL_COMPILER_ERROR), so default to CUDA; BLENDER_GPU=OPTIX to try it.
# BLENDER_LIB points every build script at the library clone (the scripts default to /Users/dhruv/blender on the Mac).
GPUENV="export BLENDER_GPU=${BLENDER_GPU:-CUDA} BLENDER_LIB=/work/blender-lib ${VAST_ENV:-};"
run() { sshx "$GPUENV cd /work/repo && $*"; }
sync() { sshx "cd /work/repo && GIT_SSH_COMMAND='ssh -i /root/.ssh/deploy_repo' git fetch -q --depth 1 origin main && git reset -q --hard origin/main && git log --oneline -1
             cd /work/blender-lib && GIT_SSH_COMMAND='ssh -i /root/.ssh/deploy_lib' git fetch -q --depth 1 origin main && git reset -q --hard origin/main && git log --oneline -1"; }
blender() { local s=$1; shift; sshx "$GPUENV cd /work/repo && /work/blender/blender -b --factory-startup --python $s $*"; }
batch() {
  local s=$1; shift; local name=$(basename ${s:h}); local log=/work/logs/$name-$(date -u +%H%M%S).log
  # nvidia-smi samples the GPU every 5 s for the life of the job; the END line reports the average (PENDING B23)
  sshx "cat > /work/batch.sh <<'EOS'
#!/bin/bash
$GPUENV cd /work/repo
echo \"=== START \$(date -u +%FT%TZ) $s $*\"
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits -l 5 > $log.gpu 2>/dev/null &
SMI=\$!
/work/blender/blender -b --factory-startup --python-exit-code 1 --python $s $*
RC=\$?
kill \$SMI 2>/dev/null
awk -F, '{s+=\$1; n++; if (\$1>=70) b++} END {if (n) printf(\"=== GPU avg %.0f%% over %d samples (%d s), >=70%% for %.0f%% of the time\\n\", s/n, n, n*5, 100*b/n)}' $log.gpu
echo \"=== END rc=\$RC \$(date -u +%FT%TZ)\"
EOS
chmod +x /work/batch.sh; nohup /work/batch.sh > $log 2>&1 &
echo $log > /work/logs/latest; echo $log"
}
wait() {
  need_instance; local log=${1:-$(sshx cat /work/logs/latest)}; local seen=0
  while true; do
    local out=$(sshx "grep -n -E '=== END|=== GPU|BUILT|REVIEW|RENDERED|Error|Traceback' $log | tail -n +$((seen+1))" || true)
    [[ -n $out ]] && { print -r -- "$out"; seen=$((seen + $(print -r -- "$out" | wc -l))); }
    if sshx "grep -q '=== END' $log"; then local rc=$(sshx "grep -o 'rc=[0-9]*' $log | tail -1 | cut -d= -f2"); echo "batch finished rc=$rc ($log)"; return $rc; fi
    sleep ${VAST_POLL:-30}
  done
}
log() { sshx "tail -n ${1:-40} \$(cat /work/logs/latest)"; }
pull() { need_instance; for p in "$@"; do rsync -azv -e "ssh -i $KEY -p $PORT -o LogLevel=ERROR" "root@$HOST:/work/repo/$p" "$ROOT/${p:h}/"; done; }
push() { need_instance; for p in "$@"; do rsync -az -e "ssh -i $KEY -p $PORT -o LogLevel=ERROR" "$ROOT/$p" "root@$HOST:/work/repo/${p:h}/"; done; }
status() { need_instance; api GET "/v0/instances/$ID/" | py "
import sys,json
d=json.load(sys.stdin); d=d.get('instances',d)
if isinstance(d,list): d=d[0] if d else {}
print('id', d.get('id'), '|', d.get('actual_status'), '|', d.get('gpu_name'), '| \$%.3f/h incl. disk' % (d.get('dph_total') or 0), '|', d.get('geolocation'))"; }
# Every instance on the account (v1 list; the v0 list is deprecated and silently hid a stray box on 26 Sep).
list() { api GET "/v1/instances/" | py "
import sys,json
v=json.load(sys.stdin).get('instances',[])
print(len(v), 'instance(s)')
for x in v: print(' ', x['id'], x.get('label'), x.get('actual_status'), x.get('gpu_name'), '\$%.3f/h' % (x.get('dph_total') or 0))"; }
down() { need_instance; api DELETE "/v0/instances/$ID/" | py "import sys,json;d=json.load(sys.stdin);print('destroyed' if d.get('success') else d)"; rm -f $STATE; ledger down $ID; }
cost() {  # cost [start|end] — the session-start / session-end line Dhruv asked for (PENDING §5c 2026-09-26)
  local now=$(credit)
  [[ $1 == start ]] && ledger start
  echo "credit: \$$now"
  list | sed 's/^/  /'
  if [[ -f $LEDGER ]]; then
    local at=$(grep ',start,' $LEDGER | tail -1); local upl=$(grep ',up,' $LEDGER | tail -1)
    [[ -n $at ]] && py "import sys;a=float(sys.argv[1]);b=float(sys.argv[2]);print('session spend since %s: \$%.3f' % (sys.argv[3], a-b))" "${at##*,}" "$now" "${at%%,*}"
    [[ -n $upl && $upl > $at ]] && py "import sys;a=float(sys.argv[1]);b=float(sys.argv[2]);print('spend since box %s came up (%s): \$%.3f' % (sys.argv[4], sys.argv[3], a-b))" "${upl##*,}" "$now" "${upl%%,*}" "$(print -r -- $upl | cut -d, -f3)"
  fi
  [[ $1 == end ]] && ledger end
  return 0
}

cmd=${1:-help}; shift || true
case $cmd in
  search|up|run|sync|blender|batch|wait|log|pull|push|status|down|list|cost) $cmd "$@" ;;
  ssh) sshx ;;
  *) sed -n '2,20p' $0 ;;
esac
