
for job in test pack; do
   mkdir -p $job
   irmasim  --output_dir $job -w workload_$job.json options.json
done
