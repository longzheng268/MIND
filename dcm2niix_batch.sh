#!/bin/bash
# 批量将RAWData下的DICOM转为NIfTI，增强容错和日志记录

RAW_ROOT="./data/RAWData"
NIFTI_ROOT="./data/NIfTI"
LOG_FILE="./logs/dcm2niix_batch.log"

mkdir -p "$NIFTI_ROOT"
mkdir -p "$(dirname "$LOG_FILE")"

echo "批量DICOM转NIfTI开始：$(date)" | tee -a "$LOG_FILE"

groups=(HC PD prodromal)
for group in "${groups[@]}"; do
  in_dir="$RAW_ROOT/$group"
  out_root="$NIFTI_ROOT/$group"
  mkdir -p "$out_root"
  if [ ! -d "$in_dir" ]; then
    echo "[WARN] 组目录不存在: $in_dir，跳过" | tee -a "$LOG_FILE"
    continue
  fi
  for subj in "$in_dir"/*; do
    [ -d "$subj" ] || { echo "[WARN] 非目录或不存在: $subj，跳过" | tee -a "$LOG_FILE"; continue; }
    subj_id=$(basename "$subj")
    out_dir="$out_root/$subj_id"
    mkdir -p "$out_dir"
    # 检查DICOM文件是否存在
    dicom_count=$(find "$subj" -type f | wc -l)
    if [ "$dicom_count" -eq 0 ]; then
      echo "[WARN] $subj 没有DICOM文件，跳过" | tee -a "$LOG_FILE"
      continue
    fi
    echo "[INFO] 开始: $group/$subj_id ($dicom_count files)" | tee -a "$LOG_FILE"
    dcm2niix -z y -f %p_%s -o "$out_dir" "$subj" >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
      echo "[OK] 完成: $group/$subj_id" | tee -a "$LOG_FILE"
    else
      echo "[ERR] 失败: $group/$subj_id" | tee -a "$LOG_FILE"
    fi
  done
done

echo "批量DICOM转NIfTI结束：$(date)" | tee -a "$LOG_FILE"
