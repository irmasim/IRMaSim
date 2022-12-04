
for job in random first shortest smallest low_mem low_mem_ops; do
   mkdir -p $job
   irmasim  --output_dir $job -x workload_manager.job_selection=$job options.json
done
