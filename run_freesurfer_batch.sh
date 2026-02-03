#!/bin/bash
# 批量运行 FreeSurfer recon-all，适配 MIND 项目结构

INPUT_ROOT="./data/NIfTI"
OUTPUT_DIR="./data/Recon-Result"
LICENSE="/usr/local/freesurfer/license.txt"
MAX_PARALLEL=100  # CPU密集型，建议并行数小

# 检查 FreeSurfer 环境
if ! command -v recon-all &> /dev/null; then
  echo "未检测到 recon-all，请先配置好 FreeSurfer 环境！"
  exit 1
fi

if [ ! -d "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_DIR"
fi

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
  recon-all -i "$nii_path" -s "$sid" -sd "$OUTPUT_DIR" -all
    echo "<<< 处理完成: $sid ($group)"
}

export -f run_one
export OUTPUT_DIR
printf "%s\n" "${TASKS[@]}" | xargs -P $MAX_PARALLEL -I{} bash -c 'arr=(${0//|/ }); run_one "${arr[0]}" "${arr[1]}"' {}
  printf "%s\n" "${TASKS[@]}" | xargs -P $MAX_PARALLEL -I{} bash -c 'arr=(${0//|/ }); run_one "${arr[0]}" "${arr[1]}" "${arr[2]}"' {}

echo "全部任务执行完毕！"
