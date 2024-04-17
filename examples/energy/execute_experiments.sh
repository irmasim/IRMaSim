
for job in heuristic energy; do
   mkdir -p $job
   irmasim  --output_dir $job -w workload.json options_$job.json
done
