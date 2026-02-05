#!/bin/bash
# 自动批量运行 FastSurfer，自动查找 run_fastsurfer.sh
# 适配 MIND 项目目录结构

INPUT_ROOT="./NIfTI"
OUTPUT_DIR="./data/Recon-Result"
LICENSE="/usr/local/freesurfer/license.txt"
MAX_PARALLEL=100

# 自动查找 FastSurfer 主目录和 run_fastsurfer.sh
FASTSURFER_BIN=$(find /2025212358 -type f -name run_fastsurfer.sh | head -n 1)
if [ -z "$FASTSURFER_BIN" ]; then
  echo "未找到 run_fastsurfer.sh，请检查 FastSurfer 安装路径！"
  exit 1
fi

if [ ! -d "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_DIR"
fi

echo "使用 FastSurfer: $FASTSURFER_BIN"

# 收集所有 NIfTI 路径和被试ID
TASKS=()
for group in HC PD prodromal; do
  for subj_dir in "$INPUT_ROOT/$group"/*; do
    [ -d "$subj_dir" ] || continue
    subj=$(basename "$subj_dir")
    for nii in "$subj_dir"/*.nii*; do
      [ -f "$nii" ] || continue
      sid="${group}_${subj}"
      TASKS+=("$nii|$sid|$group")
    done
  done
done

echo "共找到 ${#TASKS[@]} 个任务，准备并行处理 (并行数: $MAX_PARALLEL) ..."

# 并行处理
function run_one() {
  local nii_path="$1"
  local sid="$2"
  local group="$3"
  mkdir -p "$OUTPUT_DIR/$group"
  echo ">>> 开始处理: $sid ($group)"
  bash "$FASTSURFER_BIN" \
    --t1 "$nii_path" \
    --sd "$OUTPUT_DIR/$group" \
    --sid "$sid" \
    --fs_license "$LICENSE" \
    --parallel \
    --device cpu \
    --allow_root
  echo "<<< 处理完成: $sid ($group)"
}

export -f run_one
export FASTSURFER_BIN OUTPUT_DIR LICENSE

printf "%s\n" "${TASKS[@]}" | xargs -P $MAX_PARALLEL -I{} bash -c 'arr=(${0//|/ }); run_one "${arr[0]}" "${arr[1]}" "${arr[2]}"' {}

echo "全部任务执行完毕！"
