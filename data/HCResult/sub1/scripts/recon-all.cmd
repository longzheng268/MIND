

#---------------------------------
# New invocation of recon-all Sat Dec  7 14:39:53 CST 2024 

 mri_convert /home/recon/HCdata/sub1/sub1.nii /home/HCResult/sub1/mri/orig/001.mgz 

#--------------------------------------------
#@# MotionCor Sat Dec  7 14:39:57 CST 2024

 cp /home/HCResult/sub1/mri/orig/001.mgz /home/HCResult/sub1/mri/rawavg.mgz 


 mri_info /home/HCResult/sub1/mri/rawavg.mgz 


 mri_convert /home/HCResult/sub1/mri/rawavg.mgz /home/HCResult/sub1/mri/orig.mgz --conform 


 mri_add_xform_to_header -c /home/HCResult/sub1/mri/transforms/talairach.xfm /home/HCResult/sub1/mri/orig.mgz /home/HCResult/sub1/mri/orig.mgz 


 mri_info /home/HCResult/sub1/mri/orig.mgz 

#--------------------------------------------
#@# Talairach Sat Dec  7 14:40:03 CST 2024

 mri_nu_correct.mni --no-rescale --i orig.mgz --o orig_nu.mgz --ants-n4 --n 1 --proto-iters 1000 --distance 50 


 talairach_avi --i orig_nu.mgz --xfm transforms/talairach.auto.xfm 

talairach_avi log file is transforms/talairach_avi.log...

 cp transforms/talairach.auto.xfm transforms/talairach.xfm 

lta_convert --src orig.mgz --trg /usr/local/freesurfer/7.4.1/average/mni305.cor.mgz --inxfm transforms/talairach.xfm --outlta transforms/talairach.xfm.lta --subject fsaverage --ltavox2vox
#--------------------------------------------
#@# Talairach Failure Detection Sat Dec  7 14:42:56 CST 2024

 talairach_afd -T 0.005 -xfm transforms/talairach.xfm 


 awk -f /usr/local/freesurfer/7.4.1/bin/extract_talairach_avi_QA.awk /home/HCResult/sub1/mri/transforms/talairach_avi.log 


 tal_QC_AZS /home/HCResult/sub1/mri/transforms/talairach_avi.log 

#--------------------------------------------
#@# Nu Intensity Correction Sat Dec  7 14:42:56 CST 2024

 mri_nu_correct.mni --i orig.mgz --o nu.mgz --uchar transforms/talairach.xfm --n 2 --ants-n4 


 mri_add_xform_to_header -c /home/HCResult/sub1/mri/transforms/talairach.xfm nu.mgz nu.mgz 

#--------------------------------------------
#@# Intensity Normalization Sat Dec  7 14:45:45 CST 2024

 mri_normalize -g 1 -seed 1234 -mprage nu.mgz T1.mgz 

#--------------------------------------------
#@# Skull Stripping Sat Dec  7 14:46:49 CST 2024

 mri_em_register -skull nu.mgz /usr/local/freesurfer/7.4.1/average/RB_all_withskull_2020_01_02.gca transforms/talairach_with_skull.lta 


 mri_watershed -T1 -brain_atlas /usr/local/freesurfer/7.4.1/average/RB_all_withskull_2020_01_02.gca transforms/talairach_with_skull.lta T1.mgz brainmask.auto.mgz 


 cp brainmask.auto.mgz brainmask.mgz 

#-------------------------------------
#@# EM Registration Sat Dec  7 14:53:30 CST 2024

 mri_em_register -uns 3 -mask brainmask.mgz nu.mgz /usr/local/freesurfer/7.4.1/average/RB_all_2020-01-02.gca transforms/talairach.lta 

#--------------------------------------
#@# CA Normalize Sat Dec  7 15:00:41 CST 2024

 mri_ca_normalize -c ctrl_pts.mgz -mask brainmask.mgz nu.mgz /usr/local/freesurfer/7.4.1/average/RB_all_2020-01-02.gca transforms/talairach.lta norm.mgz 

#--------------------------------------
#@# CA Reg Sat Dec  7 15:01:22 CST 2024

 mri_ca_register -nobigventricles -T transforms/talairach.lta -align-after -mask brainmask.mgz norm.mgz /usr/local/freesurfer/7.4.1/average/RB_all_2020-01-02.gca transforms/talairach.m3z 

#--------------------------------------
#@# SubCort Seg Sat Dec  7 16:07:18 CST 2024

 mri_ca_label -relabel_unlikely 9 .3 -prior 0.5 -align norm.mgz transforms/talairach.m3z /usr/local/freesurfer/7.4.1/average/RB_all_2020-01-02.gca aseg.auto_noCCseg.mgz 

#--------------------------------------
#@# CC Seg Sat Dec  7 16:40:27 CST 2024

 mri_cc -aseg aseg.auto_noCCseg.mgz -o aseg.auto.mgz -lta /home/HCResult/sub1/mri/transforms/cc_up.lta sub1 

#--------------------------------------
#@# Merge ASeg Sat Dec  7 16:40:48 CST 2024

 cp aseg.auto.mgz aseg.presurf.mgz 

#--------------------------------------------
#@# Intensity Normalization2 Sat Dec  7 16:40:48 CST 2024

 mri_normalize -seed 1234 -mprage -aseg aseg.presurf.mgz -mask brainmask.mgz norm.mgz brain.mgz 

#--------------------------------------------
#@# Mask BFS Sat Dec  7 16:42:22 CST 2024

 mri_mask -T 5 brain.mgz brainmask.mgz brain.finalsurfs.mgz 

#--------------------------------------------
#@# WM Segmentation Sat Dec  7 16:42:23 CST 2024

 AntsDenoiseImageFs -i brain.mgz -o antsdn.brain.mgz 


 mri_segment -wsizemm 13 -mprage antsdn.brain.mgz wm.seg.mgz 


 mri_edit_wm_with_aseg -keep-in wm.seg.mgz brain.mgz aseg.presurf.mgz wm.asegedit.mgz 


 mri_pretess wm.asegedit.mgz wm norm.mgz wm.mgz 

#--------------------------------------------
#@# Fill Sat Dec  7 16:44:06 CST 2024

 mri_fill -a ../scripts/ponscc.cut.log -xform transforms/talairach.lta -segmentation aseg.presurf.mgz -ctab /usr/local/freesurfer/7.4.1/SubCorticalMassLUT.txt wm.mgz filled.mgz 

 cp filled.mgz filled.auto.mgz
#--------------------------------------------
#@# Tessellate lh Sat Dec  7 16:44:43 CST 2024

 mri_pretess ../mri/filled.mgz 255 ../mri/norm.mgz ../mri/filled-pretess255.mgz 


 mri_tessellate ../mri/filled-pretess255.mgz 255 ../surf/lh.orig.nofix 


 rm -f ../mri/filled-pretess255.mgz 


 mris_extract_main_component ../surf/lh.orig.nofix ../surf/lh.orig.nofix 

#--------------------------------------------
#@# Tessellate rh Sat Dec  7 16:44:47 CST 2024

 mri_pretess ../mri/filled.mgz 127 ../mri/norm.mgz ../mri/filled-pretess127.mgz 


 mri_tessellate ../mri/filled-pretess127.mgz 127 ../surf/rh.orig.nofix 


 rm -f ../mri/filled-pretess127.mgz 


 mris_extract_main_component ../surf/rh.orig.nofix ../surf/rh.orig.nofix 

#--------------------------------------------
#@# Smooth1 lh Sat Dec  7 16:44:51 CST 2024

 mris_smooth -nw -seed 1234 ../surf/lh.orig.nofix ../surf/lh.smoothwm.nofix 

#--------------------------------------------
#@# Smooth1 rh Sat Dec  7 16:44:53 CST 2024

 mris_smooth -nw -seed 1234 ../surf/rh.orig.nofix ../surf/rh.smoothwm.nofix 

#--------------------------------------------
#@# Inflation1 lh Sat Dec  7 16:44:55 CST 2024

 mris_inflate -no-save-sulc ../surf/lh.smoothwm.nofix ../surf/lh.inflated.nofix 

#--------------------------------------------
#@# Inflation1 rh Sat Dec  7 16:45:08 CST 2024

 mris_inflate -no-save-sulc ../surf/rh.smoothwm.nofix ../surf/rh.inflated.nofix 

#--------------------------------------------
#@# QSphere lh Sat Dec  7 16:45:21 CST 2024

 mris_sphere -q -p 6 -a 128 -seed 1234 ../surf/lh.inflated.nofix ../surf/lh.qsphere.nofix 

#--------------------------------------------
#@# QSphere rh Sat Dec  7 16:47:03 CST 2024

 mris_sphere -q -p 6 -a 128 -seed 1234 ../surf/rh.inflated.nofix ../surf/rh.qsphere.nofix 

#@# Fix Topology lh Sat Dec  7 16:48:44 CST 2024

 mris_fix_topology -mgz -sphere qsphere.nofix -inflated inflated.nofix -orig orig.nofix -out orig.premesh -ga -seed 1234 sub1 lh 

#@# Fix Topology rh Sat Dec  7 16:49:38 CST 2024

 mris_fix_topology -mgz -sphere qsphere.nofix -inflated inflated.nofix -orig orig.nofix -out orig.premesh -ga -seed 1234 sub1 rh 


 mris_euler_number ../surf/lh.orig.premesh 


 mris_euler_number ../surf/rh.orig.premesh 


 mris_remesh --remesh --iters 3 --input /home/HCResult/sub1/surf/lh.orig.premesh --output /home/HCResult/sub1/surf/lh.orig 


 mris_remesh --remesh --iters 3 --input /home/HCResult/sub1/surf/rh.orig.premesh --output /home/HCResult/sub1/surf/rh.orig 


 mris_remove_intersection ../surf/lh.orig ../surf/lh.orig 


 rm -f ../surf/lh.inflated 


 mris_remove_intersection ../surf/rh.orig ../surf/rh.orig 


 rm -f ../surf/rh.inflated 

#--------------------------------------------
#@# AutoDetGWStats lh Sat Dec  7 16:51:41 CST 2024
cd /home/HCResult/sub1/mri
mris_autodet_gwstats --o ../surf/autodet.gw.stats.lh.dat --i brain.finalsurfs.mgz --wm wm.mgz --surf ../surf/lh.orig.premesh
#--------------------------------------------
#@# AutoDetGWStats rh Sat Dec  7 16:51:44 CST 2024
cd /home/HCResult/sub1/mri
mris_autodet_gwstats --o ../surf/autodet.gw.stats.rh.dat --i brain.finalsurfs.mgz --wm wm.mgz --surf ../surf/rh.orig.premesh
#--------------------------------------------
#@# WhitePreAparc lh Sat Dec  7 16:51:46 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.lh.dat --wm wm.mgz --threads 1 --invol brain.finalsurfs.mgz --lh --i ../surf/lh.orig --o ../surf/lh.white.preaparc --white --seg aseg.presurf.mgz --nsmooth 5
#--------------------------------------------
#@# WhitePreAparc rh Sat Dec  7 16:54:44 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.rh.dat --wm wm.mgz --threads 1 --invol brain.finalsurfs.mgz --rh --i ../surf/rh.orig --o ../surf/rh.white.preaparc --white --seg aseg.presurf.mgz --nsmooth 5
#--------------------------------------------
#@# CortexLabel lh Sat Dec  7 16:57:48 CST 2024
cd /home/HCResult/sub1/mri
mri_label2label --label-cortex ../surf/lh.white.preaparc aseg.presurf.mgz 0 ../label/lh.cortex.label
#--------------------------------------------
#@# CortexLabel+HipAmyg lh Sat Dec  7 16:57:59 CST 2024
cd /home/HCResult/sub1/mri
mri_label2label --label-cortex ../surf/lh.white.preaparc aseg.presurf.mgz 1 ../label/lh.cortex+hipamyg.label
#--------------------------------------------
#@# CortexLabel rh Sat Dec  7 16:58:10 CST 2024
cd /home/HCResult/sub1/mri
mri_label2label --label-cortex ../surf/rh.white.preaparc aseg.presurf.mgz 0 ../label/rh.cortex.label
#--------------------------------------------
#@# CortexLabel+HipAmyg rh Sat Dec  7 16:58:21 CST 2024
cd /home/HCResult/sub1/mri
mri_label2label --label-cortex ../surf/rh.white.preaparc aseg.presurf.mgz 1 ../label/rh.cortex+hipamyg.label
#--------------------------------------------
#@# Smooth2 lh Sat Dec  7 16:58:32 CST 2024

 mris_smooth -n 3 -nw -seed 1234 ../surf/lh.white.preaparc ../surf/lh.smoothwm 

#--------------------------------------------
#@# Smooth2 rh Sat Dec  7 16:58:35 CST 2024

 mris_smooth -n 3 -nw -seed 1234 ../surf/rh.white.preaparc ../surf/rh.smoothwm 

#--------------------------------------------
#@# Inflation2 lh Sat Dec  7 16:58:38 CST 2024

 mris_inflate ../surf/lh.smoothwm ../surf/lh.inflated 

#--------------------------------------------
#@# Inflation2 rh Sat Dec  7 16:58:54 CST 2024

 mris_inflate ../surf/rh.smoothwm ../surf/rh.inflated 

#--------------------------------------------
#@# Curv .H and .K lh Sat Dec  7 16:59:09 CST 2024

 mris_curvature -w -seed 1234 lh.white.preaparc 


 mris_curvature -seed 1234 -thresh .999 -n -a 5 -w -distances 10 10 lh.inflated 

#--------------------------------------------
#@# Curv .H and .K rh Sat Dec  7 16:59:52 CST 2024

 mris_curvature -w -seed 1234 rh.white.preaparc 


 mris_curvature -seed 1234 -thresh .999 -n -a 5 -w -distances 10 10 rh.inflated 

#--------------------------------------------
#@# Sphere lh Sat Dec  7 17:00:34 CST 2024

 mris_sphere -seed 1234 ../surf/lh.inflated ../surf/lh.sphere 

#--------------------------------------------
#@# Sphere rh Sat Dec  7 17:05:34 CST 2024

 mris_sphere -seed 1234 ../surf/rh.inflated ../surf/rh.sphere 

#--------------------------------------------
#@# Surf Reg lh Sat Dec  7 17:11:25 CST 2024

 mris_register -curv ../surf/lh.sphere /usr/local/freesurfer/7.4.1/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/lh.sphere.reg 


 ln -sf lh.sphere.reg lh.fsaverage.sphere.reg 

#--------------------------------------------
#@# Surf Reg rh Sat Dec  7 17:16:46 CST 2024

 mris_register -curv ../surf/rh.sphere /usr/local/freesurfer/7.4.1/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/rh.sphere.reg 


 ln -sf rh.sphere.reg rh.fsaverage.sphere.reg 

#--------------------------------------------
#@# Jacobian white lh Sat Dec  7 17:22:19 CST 2024

 mris_jacobian ../surf/lh.white.preaparc ../surf/lh.sphere.reg ../surf/lh.jacobian_white 

#--------------------------------------------
#@# Jacobian white rh Sat Dec  7 17:22:20 CST 2024

 mris_jacobian ../surf/rh.white.preaparc ../surf/rh.sphere.reg ../surf/rh.jacobian_white 

#--------------------------------------------
#@# AvgCurv lh Sat Dec  7 17:22:21 CST 2024

 mrisp_paint -a 5 /usr/local/freesurfer/7.4.1/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/lh.sphere.reg ../surf/lh.avg_curv 

#--------------------------------------------
#@# AvgCurv rh Sat Dec  7 17:22:22 CST 2024

 mrisp_paint -a 5 /usr/local/freesurfer/7.4.1/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/rh.sphere.reg ../surf/rh.avg_curv 

#-----------------------------------------
#@# Cortical Parc lh Sat Dec  7 17:22:23 CST 2024

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 lh ../surf/lh.sphere.reg /usr/local/freesurfer/7.4.1/average/lh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.annot 

#-----------------------------------------
#@# Cortical Parc rh Sat Dec  7 17:22:31 CST 2024

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 rh ../surf/rh.sphere.reg /usr/local/freesurfer/7.4.1/average/rh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.annot 

#--------------------------------------------
#@# WhiteSurfs lh Sat Dec  7 17:22:39 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.lh.dat --seg aseg.presurf.mgz --threads 1 --wm wm.mgz --invol brain.finalsurfs.mgz --lh --i ../surf/lh.white.preaparc --o ../surf/lh.white --white --nsmooth 0 --rip-label ../label/lh.cortex.label --rip-bg --rip-surf ../surf/lh.white.preaparc --aparc ../label/lh.aparc.annot
#--------------------------------------------
#@# WhiteSurfs rh Sat Dec  7 17:25:12 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.rh.dat --seg aseg.presurf.mgz --threads 1 --wm wm.mgz --invol brain.finalsurfs.mgz --rh --i ../surf/rh.white.preaparc --o ../surf/rh.white --white --nsmooth 0 --rip-label ../label/rh.cortex.label --rip-bg --rip-surf ../surf/rh.white.preaparc --aparc ../label/rh.aparc.annot
#--------------------------------------------
#@# T1PialSurf lh Sat Dec  7 17:27:58 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.lh.dat --seg aseg.presurf.mgz --threads 1 --wm wm.mgz --invol brain.finalsurfs.mgz --lh --i ../surf/lh.white --o ../surf/lh.pial.T1 --pial --nsmooth 0 --rip-label ../label/lh.cortex+hipamyg.label --pin-medial-wall ../label/lh.cortex.label --aparc ../label/lh.aparc.annot --repulse-surf ../surf/lh.white --white-surf ../surf/lh.white
#--------------------------------------------
#@# T1PialSurf rh Sat Dec  7 17:31:06 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --adgws-in ../surf/autodet.gw.stats.rh.dat --seg aseg.presurf.mgz --threads 1 --wm wm.mgz --invol brain.finalsurfs.mgz --rh --i ../surf/rh.white --o ../surf/rh.pial.T1 --pial --nsmooth 0 --rip-label ../label/rh.cortex+hipamyg.label --pin-medial-wall ../label/rh.cortex.label --aparc ../label/rh.aparc.annot --repulse-surf ../surf/rh.white --white-surf ../surf/rh.white
#@# white curv lh Sat Dec  7 17:34:21 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --curv-map ../surf/lh.white 2 10 ../surf/lh.curv
#@# white area lh Sat Dec  7 17:34:23 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --area-map ../surf/lh.white ../surf/lh.area
#@# pial curv lh Sat Dec  7 17:34:24 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --curv-map ../surf/lh.pial 2 10 ../surf/lh.curv.pial
#@# pial area lh Sat Dec  7 17:34:25 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --area-map ../surf/lh.pial ../surf/lh.area.pial
#@# thickness lh Sat Dec  7 17:34:26 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --thickness ../surf/lh.white ../surf/lh.pial 20 5 ../surf/lh.thickness
#@# area and vertex vol lh Sat Dec  7 17:34:52 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --thickness ../surf/lh.white ../surf/lh.pial 20 5 ../surf/lh.thickness
#@# white curv rh Sat Dec  7 17:34:54 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --curv-map ../surf/rh.white 2 10 ../surf/rh.curv
#@# white area rh Sat Dec  7 17:34:55 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --area-map ../surf/rh.white ../surf/rh.area
#@# pial curv rh Sat Dec  7 17:34:56 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --curv-map ../surf/rh.pial 2 10 ../surf/rh.curv.pial
#@# pial area rh Sat Dec  7 17:34:58 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --area-map ../surf/rh.pial ../surf/rh.area.pial
#@# thickness rh Sat Dec  7 17:34:59 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --thickness ../surf/rh.white ../surf/rh.pial 20 5 ../surf/rh.thickness
#@# area and vertex vol rh Sat Dec  7 17:35:24 CST 2024
cd /home/HCResult/sub1/mri
mris_place_surface --thickness ../surf/rh.white ../surf/rh.pial 20 5 ../surf/rh.thickness

#-----------------------------------------
#@# Curvature Stats lh Sat Dec  7 17:35:26 CST 2024

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/lh.curv.stats -F smoothwm sub1 lh curv sulc 


#-----------------------------------------
#@# Curvature Stats rh Sat Dec  7 17:35:28 CST 2024

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/rh.curv.stats -F smoothwm sub1 rh curv sulc 

#--------------------------------------------
#@# Cortical ribbon mask Sat Dec  7 17:35:30 CST 2024

 mris_volmask --aseg_name aseg.presurf --label_left_white 2 --label_left_ribbon 3 --label_right_white 41 --label_right_ribbon 42 --save_ribbon sub1 

#-----------------------------------------
#@# Cortical Parc 2 lh Sat Dec  7 17:41:19 CST 2024

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 lh ../surf/lh.sphere.reg /usr/local/freesurfer/7.4.1/average/lh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.a2009s.annot 

#-----------------------------------------
#@# Cortical Parc 2 rh Sat Dec  7 17:41:30 CST 2024

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 rh ../surf/rh.sphere.reg /usr/local/freesurfer/7.4.1/average/rh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.a2009s.annot 

#-----------------------------------------
#@# Cortical Parc 3 lh Sat Dec  7 17:41:42 CST 2024

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 lh ../surf/lh.sphere.reg /usr/local/freesurfer/7.4.1/average/lh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# Cortical Parc 3 rh Sat Dec  7 17:41:51 CST 2024

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub1 rh ../surf/rh.sphere.reg /usr/local/freesurfer/7.4.1/average/rh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# WM/GM Contrast lh Sat Dec  7 17:41:59 CST 2024

 pctsurfcon --s sub1 --lh-only 

#-----------------------------------------
#@# WM/GM Contrast rh Sat Dec  7 17:42:02 CST 2024

 pctsurfcon --s sub1 --rh-only 

#-----------------------------------------
#@# Relabel Hypointensities Sat Dec  7 17:42:05 CST 2024

 mri_relabel_hypointensities aseg.presurf.mgz ../surf aseg.presurf.hypos.mgz 

#-----------------------------------------
#@# APas-to-ASeg Sat Dec  7 17:42:17 CST 2024

 mri_surf2volseg --o aseg.mgz --i aseg.presurf.hypos.mgz --fix-presurf-with-ribbon /home/HCResult/sub1/mri/ribbon.mgz --threads 1 --lh-cortex-mask /home/HCResult/sub1/label/lh.cortex.label --lh-white /home/HCResult/sub1/surf/lh.white --lh-pial /home/HCResult/sub1/surf/lh.pial --rh-cortex-mask /home/HCResult/sub1/label/rh.cortex.label --rh-white /home/HCResult/sub1/surf/rh.white --rh-pial /home/HCResult/sub1/surf/rh.pial 


 mri_brainvol_stats --subject sub1 

#-----------------------------------------
#@# AParc-to-ASeg aparc Sat Dec  7 17:42:28 CST 2024

 mri_surf2volseg --o aparc+aseg.mgz --label-cortex --i aseg.mgz --threads 1 --lh-annot /home/HCResult/sub1/label/lh.aparc.annot 1000 --lh-cortex-mask /home/HCResult/sub1/label/lh.cortex.label --lh-white /home/HCResult/sub1/surf/lh.white --lh-pial /home/HCResult/sub1/surf/lh.pial --rh-annot /home/HCResult/sub1/label/rh.aparc.annot 2000 --rh-cortex-mask /home/HCResult/sub1/label/rh.cortex.label --rh-white /home/HCResult/sub1/surf/rh.white --rh-pial /home/HCResult/sub1/surf/rh.pial 

#-----------------------------------------
#@# AParc-to-ASeg aparc.a2009s Sat Dec  7 17:44:40 CST 2024

 mri_surf2volseg --o aparc.a2009s+aseg.mgz --label-cortex --i aseg.mgz --threads 1 --lh-annot /home/HCResult/sub1/label/lh.aparc.a2009s.annot 11100 --lh-cortex-mask /home/HCResult/sub1/label/lh.cortex.label --lh-white /home/HCResult/sub1/surf/lh.white --lh-pial /home/HCResult/sub1/surf/lh.pial --rh-annot /home/HCResult/sub1/label/rh.aparc.a2009s.annot 12100 --rh-cortex-mask /home/HCResult/sub1/label/rh.cortex.label --rh-white /home/HCResult/sub1/surf/rh.white --rh-pial /home/HCResult/sub1/surf/rh.pial 

#-----------------------------------------
#@# AParc-to-ASeg aparc.DKTatlas Sat Dec  7 17:46:52 CST 2024

 mri_surf2volseg --o aparc.DKTatlas+aseg.mgz --label-cortex --i aseg.mgz --threads 1 --lh-annot /home/HCResult/sub1/label/lh.aparc.DKTatlas.annot 1000 --lh-cortex-mask /home/HCResult/sub1/label/lh.cortex.label --lh-white /home/HCResult/sub1/surf/lh.white --lh-pial /home/HCResult/sub1/surf/lh.pial --rh-annot /home/HCResult/sub1/label/rh.aparc.DKTatlas.annot 2000 --rh-cortex-mask /home/HCResult/sub1/label/rh.cortex.label --rh-white /home/HCResult/sub1/surf/rh.white --rh-pial /home/HCResult/sub1/surf/rh.pial 

#-----------------------------------------
#@# WMParc Sat Dec  7 17:49:04 CST 2024

 mri_surf2volseg --o wmparc.mgz --label-wm --i aparc+aseg.mgz --threads 1 --lh-annot /home/HCResult/sub1/label/lh.aparc.annot 3000 --lh-cortex-mask /home/HCResult/sub1/label/lh.cortex.label --lh-white /home/HCResult/sub1/surf/lh.white --lh-pial /home/HCResult/sub1/surf/lh.pial --rh-annot /home/HCResult/sub1/label/rh.aparc.annot 4000 --rh-cortex-mask /home/HCResult/sub1/label/rh.cortex.label --rh-white /home/HCResult/sub1/surf/rh.white --rh-pial /home/HCResult/sub1/surf/rh.pial 


 mri_segstats --seed 1234 --seg mri/wmparc.mgz --sum stats/wmparc.stats --pv mri/norm.mgz --excludeid 0 --brainmask mri/brainmask.mgz --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --subject sub1 --surf-wm-vol --ctab /usr/local/freesurfer/7.4.1/WMParcStatsLUT.txt --etiv 

#-----------------------------------------
#@# Parcellation Stats lh Sat Dec  7 17:54:10 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab sub1 lh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.pial.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab sub1 lh pial 

#-----------------------------------------
#@# Parcellation Stats rh Sat Dec  7 17:54:30 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab sub1 rh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.pial.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab sub1 rh pial 

#-----------------------------------------
#@# Parcellation Stats 2 lh Sat Dec  7 17:54:50 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.a2009s.stats -b -a ../label/lh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab sub1 lh white 

#-----------------------------------------
#@# Parcellation Stats 2 rh Sat Dec  7 17:55:01 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.a2009s.stats -b -a ../label/rh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab sub1 rh white 

#-----------------------------------------
#@# Parcellation Stats 3 lh Sat Dec  7 17:55:12 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.DKTatlas.stats -b -a ../label/lh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab sub1 lh white 

#-----------------------------------------
#@# Parcellation Stats 3 rh Sat Dec  7 17:55:22 CST 2024

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.DKTatlas.stats -b -a ../label/rh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab sub1 rh white 

#--------------------------------------------
#@# ASeg Stats Sat Dec  7 17:55:32 CST 2024

 mri_segstats --seed 1234 --seg mri/aseg.mgz --sum stats/aseg.stats --pv mri/norm.mgz --empty --brainmask mri/brainmask.mgz --brain-vol-from-seg --excludeid 0 --excl-ctxgmwm --supratent --subcortgray --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --etiv --surf-wm-vol --surf-ctx-vol --totalgray --euler --ctab /usr/local/freesurfer/7.4.1/ASegStatsLUT.txt --subject sub1 

INFO: fsaverage subject does not exist in SUBJECTS_DIR
INFO: Creating symlink to fsaverage subject...

 cd /home/HCResult; ln -s /usr/local/freesurfer/7.4.1/subjects/fsaverage; cd - 

#--------------------------------------------
#@# BA_exvivo Labels lh Sat Dec  7 17:57:55 CST 2024

 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA1_exvivo.label --trgsubject sub1 --trglabel ./lh.BA1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA2_exvivo.label --trgsubject sub1 --trglabel ./lh.BA2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA3a_exvivo.label --trgsubject sub1 --trglabel ./lh.BA3a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA3b_exvivo.label --trgsubject sub1 --trglabel ./lh.BA3b_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA4a_exvivo.label --trgsubject sub1 --trglabel ./lh.BA4a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA4p_exvivo.label --trgsubject sub1 --trglabel ./lh.BA4p_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA6_exvivo.label --trgsubject sub1 --trglabel ./lh.BA6_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA44_exvivo.label --trgsubject sub1 --trglabel ./lh.BA44_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA45_exvivo.label --trgsubject sub1 --trglabel ./lh.BA45_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.V1_exvivo.label --trgsubject sub1 --trglabel ./lh.V1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.V2_exvivo.label --trgsubject sub1 --trglabel ./lh.V2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.MT_exvivo.label --trgsubject sub1 --trglabel ./lh.MT_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.entorhinal_exvivo.label --trgsubject sub1 --trglabel ./lh.entorhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.perirhinal_exvivo.label --trgsubject sub1 --trglabel ./lh.perirhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.FG1.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.FG1.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.FG2.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.FG2.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.FG3.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.FG3.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.FG4.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.FG4.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.hOc1.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.hOc1.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.hOc2.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.hOc2.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.hOc3v.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.hOc3v.mpm.vpnl.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.hOc4v.mpm.vpnl.label --trgsubject sub1 --trglabel ./lh.hOc4v.mpm.vpnl.label --hemi lh --regmethod surface 


 mris_label2annot --s sub1 --ctab /usr/local/freesurfer/7.4.1/average/colortable_vpnl.txt --hemi lh --a mpm.vpnl --maxstatwinner --noverbose --l lh.FG1.mpm.vpnl.label --l lh.FG2.mpm.vpnl.label --l lh.FG3.mpm.vpnl.label --l lh.FG4.mpm.vpnl.label --l lh.hOc1.mpm.vpnl.label --l lh.hOc2.mpm.vpnl.label --l lh.hOc3v.mpm.vpnl.label --l lh.hOc4v.mpm.vpnl.label 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA1_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA2_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA3a_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA3a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA3b_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA3b_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA4a_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA4a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA4p_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA4p_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA6_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA6_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA44_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA44_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.BA45_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.BA45_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.V1_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.V1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.V2_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.V2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.MT_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.MT_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.entorhinal_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.entorhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/lh.perirhinal_exvivo.thresh.label --trgsubject sub1 --trglabel ./lh.perirhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mris_label2annot --s sub1 --hemi lh --ctab /usr/local/freesurfer/7.4.1/average/colortable_BA.txt --l lh.BA1_exvivo.label --l lh.BA2_exvivo.label --l lh.BA3a_exvivo.label --l lh.BA3b_exvivo.label --l lh.BA4a_exvivo.label --l lh.BA4p_exvivo.label --l lh.BA6_exvivo.label --l lh.BA44_exvivo.label --l lh.BA45_exvivo.label --l lh.V1_exvivo.label --l lh.V2_exvivo.label --l lh.MT_exvivo.label --l lh.perirhinal_exvivo.label --l lh.entorhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s sub1 --hemi lh --ctab /usr/local/freesurfer/7.4.1/average/colortable_BA.txt --l lh.BA1_exvivo.thresh.label --l lh.BA2_exvivo.thresh.label --l lh.BA3a_exvivo.thresh.label --l lh.BA3b_exvivo.thresh.label --l lh.BA4a_exvivo.thresh.label --l lh.BA4p_exvivo.thresh.label --l lh.BA6_exvivo.thresh.label --l lh.BA44_exvivo.thresh.label --l lh.BA45_exvivo.thresh.label --l lh.V1_exvivo.thresh.label --l lh.V2_exvivo.thresh.label --l lh.MT_exvivo.thresh.label --l lh.perirhinal_exvivo.thresh.label --l lh.entorhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.stats -b -a ./lh.BA_exvivo.annot -c ./BA_exvivo.ctab sub1 lh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.thresh.stats -b -a ./lh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab sub1 lh white 

#--------------------------------------------
#@# BA_exvivo Labels rh Sat Dec  7 18:00:37 CST 2024

 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA1_exvivo.label --trgsubject sub1 --trglabel ./rh.BA1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA2_exvivo.label --trgsubject sub1 --trglabel ./rh.BA2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA3a_exvivo.label --trgsubject sub1 --trglabel ./rh.BA3a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA3b_exvivo.label --trgsubject sub1 --trglabel ./rh.BA3b_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA4a_exvivo.label --trgsubject sub1 --trglabel ./rh.BA4a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA4p_exvivo.label --trgsubject sub1 --trglabel ./rh.BA4p_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA6_exvivo.label --trgsubject sub1 --trglabel ./rh.BA6_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA44_exvivo.label --trgsubject sub1 --trglabel ./rh.BA44_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA45_exvivo.label --trgsubject sub1 --trglabel ./rh.BA45_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.V1_exvivo.label --trgsubject sub1 --trglabel ./rh.V1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.V2_exvivo.label --trgsubject sub1 --trglabel ./rh.V2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.MT_exvivo.label --trgsubject sub1 --trglabel ./rh.MT_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.entorhinal_exvivo.label --trgsubject sub1 --trglabel ./rh.entorhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.perirhinal_exvivo.label --trgsubject sub1 --trglabel ./rh.perirhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.FG1.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.FG1.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.FG2.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.FG2.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.FG3.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.FG3.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.FG4.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.FG4.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.hOc1.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.hOc1.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.hOc2.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.hOc2.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.hOc3v.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.hOc3v.mpm.vpnl.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.hOc4v.mpm.vpnl.label --trgsubject sub1 --trglabel ./rh.hOc4v.mpm.vpnl.label --hemi rh --regmethod surface 


 mris_label2annot --s sub1 --ctab /usr/local/freesurfer/7.4.1/average/colortable_vpnl.txt --hemi rh --a mpm.vpnl --maxstatwinner --noverbose --l rh.FG1.mpm.vpnl.label --l rh.FG2.mpm.vpnl.label --l rh.FG3.mpm.vpnl.label --l rh.FG4.mpm.vpnl.label --l rh.hOc1.mpm.vpnl.label --l rh.hOc2.mpm.vpnl.label --l rh.hOc3v.mpm.vpnl.label --l rh.hOc4v.mpm.vpnl.label 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA1_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA2_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA3a_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA3a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA3b_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA3b_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA4a_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA4a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA4p_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA4p_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA6_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA6_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA44_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA44_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.BA45_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.BA45_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.V1_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.V1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.V2_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.V2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.MT_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.MT_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.entorhinal_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.entorhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /home/HCResult/fsaverage/label/rh.perirhinal_exvivo.thresh.label --trgsubject sub1 --trglabel ./rh.perirhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mris_label2annot --s sub1 --hemi rh --ctab /usr/local/freesurfer/7.4.1/average/colortable_BA.txt --l rh.BA1_exvivo.label --l rh.BA2_exvivo.label --l rh.BA3a_exvivo.label --l rh.BA3b_exvivo.label --l rh.BA4a_exvivo.label --l rh.BA4p_exvivo.label --l rh.BA6_exvivo.label --l rh.BA44_exvivo.label --l rh.BA45_exvivo.label --l rh.V1_exvivo.label --l rh.V2_exvivo.label --l rh.MT_exvivo.label --l rh.perirhinal_exvivo.label --l rh.entorhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s sub1 --hemi rh --ctab /usr/local/freesurfer/7.4.1/average/colortable_BA.txt --l rh.BA1_exvivo.thresh.label --l rh.BA2_exvivo.thresh.label --l rh.BA3a_exvivo.thresh.label --l rh.BA3b_exvivo.thresh.label --l rh.BA4a_exvivo.thresh.label --l rh.BA4p_exvivo.thresh.label --l rh.BA6_exvivo.thresh.label --l rh.BA44_exvivo.thresh.label --l rh.BA45_exvivo.thresh.label --l rh.V1_exvivo.thresh.label --l rh.V2_exvivo.thresh.label --l rh.MT_exvivo.thresh.label --l rh.perirhinal_exvivo.thresh.label --l rh.entorhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.stats -b -a ./rh.BA_exvivo.annot -c ./BA_exvivo.ctab sub1 rh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.thresh.stats -b -a ./rh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab sub1 rh white 

#--------------------------------------------
#@# Qdec Cache preproc lh thickness fsaverage Sat Dec  7 18:03:19 CST 2024

 mris_preproc --s sub1 --hemi lh --meas thickness --target fsaverage --out lh.thickness.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh area fsaverage Sat Dec  7 18:03:22 CST 2024

 mris_preproc --s sub1 --hemi lh --meas area --target fsaverage --out lh.area.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh area.pial fsaverage Sat Dec  7 18:03:27 CST 2024

 mris_preproc --s sub1 --hemi lh --meas area.pial --target fsaverage --out lh.area.pial.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh volume fsaverage Sat Dec  7 18:03:32 CST 2024

 mris_preproc --s sub1 --hemi lh --meas volume --target fsaverage --out lh.volume.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh curv fsaverage Sat Dec  7 18:03:37 CST 2024

 mris_preproc --s sub1 --hemi lh --meas curv --target fsaverage --out lh.curv.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh sulc fsaverage Sat Dec  7 18:03:41 CST 2024

 mris_preproc --s sub1 --hemi lh --meas sulc --target fsaverage --out lh.sulc.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh white.K fsaverage Sat Dec  7 18:03:45 CST 2024

 mris_preproc --s sub1 --hemi lh --meas white.K --target fsaverage --out lh.white.K.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh white.H fsaverage Sat Dec  7 18:03:48 CST 2024

 mris_preproc --s sub1 --hemi lh --meas white.H --target fsaverage --out lh.white.H.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh jacobian_white fsaverage Sat Dec  7 18:03:52 CST 2024

 mris_preproc --s sub1 --hemi lh --meas jacobian_white --target fsaverage --out lh.jacobian_white.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc lh w-g.pct.mgh fsaverage Sat Dec  7 18:03:56 CST 2024

 mris_preproc --s sub1 --hemi lh --meas w-g.pct.mgh --target fsaverage --out lh.w-g.pct.mgh.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh thickness fsaverage Sat Dec  7 18:03:59 CST 2024

 mris_preproc --s sub1 --hemi rh --meas thickness --target fsaverage --out rh.thickness.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh area fsaverage Sat Dec  7 18:04:03 CST 2024

 mris_preproc --s sub1 --hemi rh --meas area --target fsaverage --out rh.area.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh area.pial fsaverage Sat Dec  7 18:04:08 CST 2024

 mris_preproc --s sub1 --hemi rh --meas area.pial --target fsaverage --out rh.area.pial.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh volume fsaverage Sat Dec  7 18:04:13 CST 2024

 mris_preproc --s sub1 --hemi rh --meas volume --target fsaverage --out rh.volume.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh curv fsaverage Sat Dec  7 18:04:18 CST 2024

 mris_preproc --s sub1 --hemi rh --meas curv --target fsaverage --out rh.curv.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh sulc fsaverage Sat Dec  7 18:04:22 CST 2024

 mris_preproc --s sub1 --hemi rh --meas sulc --target fsaverage --out rh.sulc.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh white.K fsaverage Sat Dec  7 18:04:26 CST 2024

 mris_preproc --s sub1 --hemi rh --meas white.K --target fsaverage --out rh.white.K.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh white.H fsaverage Sat Dec  7 18:04:29 CST 2024

 mris_preproc --s sub1 --hemi rh --meas white.H --target fsaverage --out rh.white.H.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh jacobian_white fsaverage Sat Dec  7 18:04:33 CST 2024

 mris_preproc --s sub1 --hemi rh --meas jacobian_white --target fsaverage --out rh.jacobian_white.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache preproc rh w-g.pct.mgh fsaverage Sat Dec  7 18:04:37 CST 2024

 mris_preproc --s sub1 --hemi rh --meas w-g.pct.mgh --target fsaverage --out rh.w-g.pct.mgh.fsaverage.mgh 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm0 fsaverage Sat Dec  7 18:04:41 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm5 fsaverage Sat Dec  7 18:04:41 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm10 fsaverage Sat Dec  7 18:04:43 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm15 fsaverage Sat Dec  7 18:04:45 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm20 fsaverage Sat Dec  7 18:04:47 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh thickness fwhm25 fsaverage Sat Dec  7 18:04:49 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.thickness.fsaverage.mgh --tval lh.thickness.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm0 fsaverage Sat Dec  7 18:04:51 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm5 fsaverage Sat Dec  7 18:04:52 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm10 fsaverage Sat Dec  7 18:04:54 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm15 fsaverage Sat Dec  7 18:04:55 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm20 fsaverage Sat Dec  7 18:04:57 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area fwhm25 fsaverage Sat Dec  7 18:04:59 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.area.fsaverage.mgh --tval lh.area.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm0 fsaverage Sat Dec  7 18:05:02 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm5 fsaverage Sat Dec  7 18:05:03 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm10 fsaverage Sat Dec  7 18:05:04 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm15 fsaverage Sat Dec  7 18:05:06 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm20 fsaverage Sat Dec  7 18:05:08 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh area.pial fwhm25 fsaverage Sat Dec  7 18:05:10 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.area.pial.fsaverage.mgh --tval lh.area.pial.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm0 fsaverage Sat Dec  7 18:05:12 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm5 fsaverage Sat Dec  7 18:05:13 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm10 fsaverage Sat Dec  7 18:05:15 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm15 fsaverage Sat Dec  7 18:05:17 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm20 fsaverage Sat Dec  7 18:05:19 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh volume fwhm25 fsaverage Sat Dec  7 18:05:21 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.volume.fsaverage.mgh --tval lh.volume.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm0 fsaverage Sat Dec  7 18:05:23 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm5 fsaverage Sat Dec  7 18:05:24 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm10 fsaverage Sat Dec  7 18:05:26 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm15 fsaverage Sat Dec  7 18:05:27 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm20 fsaverage Sat Dec  7 18:05:29 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh curv fwhm25 fsaverage Sat Dec  7 18:05:31 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.curv.fsaverage.mgh --tval lh.curv.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm0 fsaverage Sat Dec  7 18:05:33 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm5 fsaverage Sat Dec  7 18:05:34 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm10 fsaverage Sat Dec  7 18:05:36 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm15 fsaverage Sat Dec  7 18:05:38 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm20 fsaverage Sat Dec  7 18:05:40 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh sulc fwhm25 fsaverage Sat Dec  7 18:05:42 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.sulc.fsaverage.mgh --tval lh.sulc.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm0 fsaverage Sat Dec  7 18:05:44 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm5 fsaverage Sat Dec  7 18:05:45 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm10 fsaverage Sat Dec  7 18:05:47 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm15 fsaverage Sat Dec  7 18:05:48 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm20 fsaverage Sat Dec  7 18:05:50 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.K fwhm25 fsaverage Sat Dec  7 18:05:52 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.white.K.fsaverage.mgh --tval lh.white.K.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm0 fsaverage Sat Dec  7 18:05:55 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm5 fsaverage Sat Dec  7 18:05:55 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm10 fsaverage Sat Dec  7 18:05:57 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm15 fsaverage Sat Dec  7 18:05:59 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm20 fsaverage Sat Dec  7 18:06:01 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh white.H fwhm25 fsaverage Sat Dec  7 18:06:03 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.white.H.fsaverage.mgh --tval lh.white.H.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm0 fsaverage Sat Dec  7 18:06:05 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm5 fsaverage Sat Dec  7 18:06:06 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm10 fsaverage Sat Dec  7 18:06:08 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm15 fsaverage Sat Dec  7 18:06:09 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm20 fsaverage Sat Dec  7 18:06:11 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh jacobian_white fwhm25 fsaverage Sat Dec  7 18:06:13 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.jacobian_white.fsaverage.mgh --tval lh.jacobian_white.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm0 fsaverage Sat Dec  7 18:06:16 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 0 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm5 fsaverage Sat Dec  7 18:06:17 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 5 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm10 fsaverage Sat Dec  7 18:06:18 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 10 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm15 fsaverage Sat Dec  7 18:06:20 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 15 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm20 fsaverage Sat Dec  7 18:06:22 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 20 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf lh w-g.pct.mgh fwhm25 fsaverage Sat Dec  7 18:06:24 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi lh --fwhm 25 --sval lh.w-g.pct.mgh.fsaverage.mgh --tval lh.w-g.pct.mgh.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm0 fsaverage Sat Dec  7 18:06:26 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm5 fsaverage Sat Dec  7 18:06:27 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm10 fsaverage Sat Dec  7 18:06:29 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm15 fsaverage Sat Dec  7 18:06:31 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm20 fsaverage Sat Dec  7 18:06:32 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh thickness fwhm25 fsaverage Sat Dec  7 18:06:34 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.thickness.fsaverage.mgh --tval rh.thickness.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm0 fsaverage Sat Dec  7 18:06:37 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm5 fsaverage Sat Dec  7 18:06:38 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm10 fsaverage Sat Dec  7 18:06:39 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm15 fsaverage Sat Dec  7 18:06:41 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm20 fsaverage Sat Dec  7 18:06:43 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area fwhm25 fsaverage Sat Dec  7 18:06:45 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.area.fsaverage.mgh --tval rh.area.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm0 fsaverage Sat Dec  7 18:06:47 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm5 fsaverage Sat Dec  7 18:06:48 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm10 fsaverage Sat Dec  7 18:06:50 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm15 fsaverage Sat Dec  7 18:06:52 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm20 fsaverage Sat Dec  7 18:06:54 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh area.pial fwhm25 fsaverage Sat Dec  7 18:06:56 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.area.pial.fsaverage.mgh --tval rh.area.pial.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm0 fsaverage Sat Dec  7 18:06:58 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm5 fsaverage Sat Dec  7 18:06:59 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm10 fsaverage Sat Dec  7 18:07:00 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm15 fsaverage Sat Dec  7 18:07:02 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm20 fsaverage Sat Dec  7 18:07:04 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh volume fwhm25 fsaverage Sat Dec  7 18:07:06 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.volume.fsaverage.mgh --tval rh.volume.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm0 fsaverage Sat Dec  7 18:07:08 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm5 fsaverage Sat Dec  7 18:07:09 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm10 fsaverage Sat Dec  7 18:07:11 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm15 fsaverage Sat Dec  7 18:07:13 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm20 fsaverage Sat Dec  7 18:07:15 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh curv fwhm25 fsaverage Sat Dec  7 18:07:17 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.curv.fsaverage.mgh --tval rh.curv.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm0 fsaverage Sat Dec  7 18:07:19 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm5 fsaverage Sat Dec  7 18:07:20 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm10 fsaverage Sat Dec  7 18:07:22 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm15 fsaverage Sat Dec  7 18:07:23 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm20 fsaverage Sat Dec  7 18:07:25 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh sulc fwhm25 fsaverage Sat Dec  7 18:07:27 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.sulc.fsaverage.mgh --tval rh.sulc.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm0 fsaverage Sat Dec  7 18:07:30 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm5 fsaverage Sat Dec  7 18:07:31 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm10 fsaverage Sat Dec  7 18:07:32 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm15 fsaverage Sat Dec  7 18:07:34 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm20 fsaverage Sat Dec  7 18:07:36 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.K fwhm25 fsaverage Sat Dec  7 18:07:38 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.white.K.fsaverage.mgh --tval rh.white.K.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm0 fsaverage Sat Dec  7 18:07:40 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm5 fsaverage Sat Dec  7 18:07:41 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm10 fsaverage Sat Dec  7 18:07:43 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm15 fsaverage Sat Dec  7 18:07:45 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm20 fsaverage Sat Dec  7 18:07:47 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh white.H fwhm25 fsaverage Sat Dec  7 18:07:49 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.white.H.fsaverage.mgh --tval rh.white.H.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm0 fsaverage Sat Dec  7 18:07:51 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm5 fsaverage Sat Dec  7 18:07:52 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm10 fsaverage Sat Dec  7 18:07:53 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm15 fsaverage Sat Dec  7 18:07:55 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm20 fsaverage Sat Dec  7 18:07:57 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh jacobian_white fwhm25 fsaverage Sat Dec  7 18:07:59 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.jacobian_white.fsaverage.mgh --tval rh.jacobian_white.fwhm25.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm0 fsaverage Sat Dec  7 18:08:01 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 0 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm0.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm5 fsaverage Sat Dec  7 18:08:02 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 5 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm5.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm10 fsaverage Sat Dec  7 18:08:04 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 10 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm10.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm15 fsaverage Sat Dec  7 18:08:06 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 15 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm15.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm20 fsaverage Sat Dec  7 18:08:08 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 20 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm20.fsaverage.mgh --cortex 

#--------------------------------------------
#@# Qdec Cache surf2surf rh w-g.pct.mgh fwhm25 fsaverage Sat Dec  7 18:08:10 CST 2024

 mri_surf2surf --prune --s fsaverage --hemi rh --fwhm 25 --sval rh.w-g.pct.mgh.fsaverage.mgh --tval rh.w-g.pct.mgh.fwhm25.fsaverage.mgh --cortex 

