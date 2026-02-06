#!/bin/bash
# 自动批量运行 FastSurfer，自动查找 run_fastsurfer.sh
# 适配 MIND 项目目录结构

# 使用绝对路径
INPUT_ROOT=$(realpath "./data/NIfTI")
OUTPUT_DIR=$(realpath "./data/Recon-Result")
export FS_LICENSE="/usr/local/freesurfer/license.txt"
MAX_PARALLEL=6  # FastSurfer 也是内存密集型，建议 4-8 个并行

# 自动查找 FastSurfer 主目录和 run_fastsurfer.sh
FASTSURFER_BIN=$(find /usr/local -type f -name run_fastsurfer.sh 2>/dev/null | head -n 1)
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
  [ -d "$INPUT_ROOT/$group" ] || continue
  for subj_dir in "$INPUT_ROOT/$group"/*; do
    [ -d "$subj_dir" ] || continue
    subj=$(basename "$subj_dir")
    for nii in "$subj_dir"/*.nii*; do
      [ -f "$nii" ] || continue
      # 用冒号或管道符分割，确保路径中包含空格时不会崩
      TASKS+=("$nii|$subj|$group")
    done
  done
done

echo "共找到 ${#TASKS[@]} 个任务，准备并行处理 (并行数: $MAX_PARALLEL) ..."

# 并行处理
function run_one() {
  # 使用 IFS 确保变量读取准确
  IFS='|' read -r nii_path subj group <<< "$1"
  
  # 重新组合 SID，确保唯一性
  local full_sid="${group}_${subj}"
  local target_sd="$OUTPUT_DIR/$group"
  
  mkdir -p "$target_sd"
  
  echo ">>> 开始处理: $full_sid ($group)"
  bash "$FASTSURFER_BIN" \
    --t1 "$nii_path" \
    --sd "$target_sd" \
    --sid "$full_sid" \
    --fs_license "$FS_LICENSE" \
    --parallel \
    --device cpu \
    --allow_root
  echo "<<< 处理完成: $full_sid ($group)"
}

export -f run_one
export FASTSURFER_BIN OUTPUT_DIR FS_LICENSE

# 只保留一行 printf，修正参数传递方式
printf "%s\n" "${TASKS[@]}" | xargs -n 1 -P $MAX_PARALLEL -I {} bash -c 'run_one "$@"' _ {}

echo "全部任务执行完毕！"
