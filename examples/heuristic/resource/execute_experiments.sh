

for job in random first high_gflops high_cores high_mem high_mem_bw low_power; do
   mkdir -p $job
   irmasim  --output_dir $job -x workload_manager.resource_selection=$job options.json
done
